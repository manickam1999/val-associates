"use client"

import { useState, useRef, useEffect } from "react"
import { UploadZone } from "@/components/upload-zone"
import { ProgressDisplay } from "@/components/progress-display"
import { ThemeToggle } from "@/components/theme-toggle"
import { ModeSelector, type Mode } from "@/components/mode-selector"
import { Button } from "@/components/ui/button"
import { FileListPanel } from "@/components/file-list-panel"
import { FileSummaryCard } from "@/components/file-summary-card"
import { uploadFiles, connectWebSocket, downloadExcel, type ProgressMessage } from "@/lib/api-client"
import { logger } from "@/lib/logger"
import { toast } from "sonner"

export default function Home() {
  const [files, setFiles] = useState<File[]>([])
  const [sessionId, setSessionId] = useState<string>("")
  const [selectedModes, setSelectedModes] = useState<Mode[]>(["everything", "minimal"])
  const [fileStatuses, setFileStatuses] = useState<Map<number, 'pending' | 'processing' | 'success' | 'error'>>(new Map())
  const [progress, setProgress] = useState<ProgressMessage>({
    current: 0,
    total: 0,
    status: "idle",
    message: "",
  })
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 3

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  const handleFilesSelected = (selectedFiles: File[]) => {
    setFiles((prev) => [...prev, ...selectedFiles])
    setFileStatuses((prev) => {
      const newStatuses = new Map(prev)
      const startIndex = files.length
      selectedFiles.forEach((_, index) => {
        newStatuses.set(startIndex + index, 'pending')
      })
      return newStatuses
    })
    toast.success(`${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} added`)
  }

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
    setFileStatuses((prev) => {
      const newStatuses = new Map()
      prev.forEach((status, i) => {
        if (i < index) {
          newStatuses.set(i, status)
        } else if (i > index) {
          newStatuses.set(i - 1, status)
        }
      })
      return newStatuses
    })
  }

  const handleValidationError = (error: string) => {
    toast.error(error)
  }

  const connectToWebSocket = (sid: string, totalFiles: number) => {
    const ws = connectWebSocket(
      sid,
      selectedModes,
      (message) => {
        logger.log("📨 WebSocket message received:", message)
        logger.log(`Progress: ${message.current}/${message.total} (${message.current && message.total ? Math.round((message.current / message.total) * 100) : 0}%)`)
        setProgress(message)

        // Update file statuses in real-time
        if (message.current > 0) {
          setFileStatuses((prev) => {
            const newStatuses = new Map(prev)
            const currentIndex = message.current - 1

            // Mark previous files as success if not already marked as error
            for (let i = 0; i < currentIndex; i++) {
              if (newStatuses.get(i) !== 'error') {
                newStatuses.set(i, 'success')
              }
            }

            // Update current file status
            if (message.item_status) {
              newStatuses.set(currentIndex, message.item_status)
            }

            return newStatuses
          })
        }

        if (message.status === "completed") {
          reconnectAttemptsRef.current = 0
          setWsConnected(false)
          ws.close()
          toast.success("Processing completed successfully!")

          // Mark all remaining files based on success/failure
          setFileStatuses((prev) => {
            const newStatuses = new Map(prev)
            for (let i = 0; i < files.length; i++) {
              if (!newStatuses.has(i) || newStatuses.get(i) === 'pending' || newStatuses.get(i) === 'processing') {
                newStatuses.set(i, 'success')
              }
            }
            return newStatuses
          })
        } else if (message.status === "error") {
          reconnectAttemptsRef.current = 0
          setWsConnected(false)
          ws.close()
          toast.error("Processing failed. Please try again.")
        }
      },
      (error) => {
        logger.error("WebSocket error:", error)
        setWsConnected(false)
        setProgress({
          current: 0,
          total: 0,
          status: "error",
          message: "Connection error. Please try again.",
        })
        setIsUploading(false)
        toast.error("Connection error occurred")
      },
      (event) => {
        // Handle connection close
        setWsConnected(false)
        if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          logger.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`)

          setProgress((prev) => ({
            ...prev,
            message: `Connection lost. Reconnecting... (Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`,
          }))

          reconnectTimeoutRef.current = setTimeout(() => {
            connectToWebSocket(sid, totalFiles)
          }, 2000)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setProgress({
            current: 0,
            total: 0,
            status: "error",
            message: "Failed to reconnect. Please try again.",
          })
          setIsUploading(false)
        }
      },
      () => {
        // Handle connection open
        setWsConnected(true)
      }
    )

    wsRef.current = ws
  }

  const handleSubmit = async () => {
    if (files.length === 0) return

    setIsUploading(true)
    setUploadProgress(0)
    reconnectAttemptsRef.current = 0

    // Show initial loading state
    setProgress({
      current: 0,
      total: files.length,
      status: "processing",
      message: "Uploading files to server...",
    })

    try {
      // Upload files with progress tracking
      const response = await uploadFiles(files, (loaded, total) => {
        const percentage = Math.round((loaded / total) * 100)
        setUploadProgress(percentage)
      })
      setSessionId(response.session_id)
      setUploadProgress(100)

      // Update to processing state
      setProgress({
        current: 0,
        total: response.total_files,
        status: "processing",
        message: "Connecting to server...",
      })

      // Connect to WebSocket for progress
      connectToWebSocket(response.session_id, response.total_files)
      setIsUploading(false)
    } catch (error) {
      logger.error("Upload error:", error)
      const errorMessage = error instanceof Error ? error.message : "Upload failed. Please try again."
      setProgress({
        current: 0,
        total: 0,
        status: "error",
        message: errorMessage,
      })
      setIsUploading(false)
      toast.error(errorMessage)
    }
  }

  const handleDownload = (mode?: Mode) => {
    if (sessionId) {
      downloadExcel(sessionId, mode)
    }
  }

  const handleReset = () => {
    setFiles([])
    setSessionId("")
    setFileStatuses(new Map())
    setProgress({
      current: 0,
      total: 0,
      status: "idle",
      message: "",
    })
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  const totalFileSize = files.reduce((acc, file) => acc + file.size, 0)

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">PDF Converter</h1>
            {wsConnected && (
              <span className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Connected
              </span>
            )}
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 flex-1">
        {/* Initial Upload View - No Files Selected */}
        {files.length === 0 && (
          <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
            <div className="max-w-xl w-full">
              <UploadZone
                onFilesSelected={handleFilesSelected}
                onValidationError={handleValidationError}
                disabled={isUploading || progress.status === "processing"}
                compact={false}
              />
            </div>
          </div>
        )}

        {/* Split Screen View - Files Selected */}
        {files.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6 h-full">
            {/* Left Sidebar - Controls */}
            <div className="space-y-4">
              {/* Upload Zone */}
              <UploadZone
                onFilesSelected={handleFilesSelected}
                onValidationError={handleValidationError}
                disabled={isUploading || progress.status === "processing"}
                compact={true}
              />

              {/* File Summary */}
              <FileSummaryCard fileCount={files.length} totalSize={totalFileSize} />

              {/* Mode Selection */}
              {progress.status === "idle" && (
                <ModeSelector
                  selectedModes={selectedModes}
                  onChange={setSelectedModes}
                />
              )}

              {/* Submit Button */}
              {progress.status === "idle" && (
                <Button
                  onClick={handleSubmit}
                  disabled={isUploading || selectedModes.length === 0}
                  className="w-full"
                >
                  Process Files
                </Button>
              )}

              {/* Clear Files Button */}
              {progress.status === "idle" && (
                <Button
                  onClick={handleReset}
                  variant="outline"
                  className="w-full"
                >
                  Clear All Files
                </Button>
              )}

              {/* Upload Progress */}
              {isUploading && uploadProgress < 100 && (
                <div className="rounded-lg border p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Uploading files...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Progress Display */}
              {progress.status !== "idle" && (
                <ProgressDisplay
                  current={progress.current}
                  total={progress.total}
                  status={progress.status}
                  message={progress.message}
                  elapsedTime={progress.elapsed_time}
                  itemStatus={progress.item_status}
                  successCount={progress.success_count}
                  failedCount={progress.failed_count}
                  failedFiles={progress.failed_files}
                  selectedModes={selectedModes}
                  onDownload={handleDownload}
                  onReset={handleReset}
                />
              )}
            </div>

            {/* Right Panel - File List */}
            <div>
              <FileListPanel
                files={files}
                onRemoveFile={handleRemoveFile}
                currentProcessingIndex={progress.current - 1}
                fileStatuses={fileStatuses}
                disabled={isUploading || progress.status === "processing"}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t mt-auto">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>© 2025 Vel Associates. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

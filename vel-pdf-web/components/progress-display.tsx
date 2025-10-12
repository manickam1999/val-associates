"use client"

import { Check, FileText, Loader2, XCircle, Clock, AlertCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Mode } from "@/components/mode-selector"
import type { ProgressStatus, ItemStatus } from "@/lib/api-client"

interface ProgressDisplayProps {
  current: number
  total: number
  status: ProgressStatus
  message: string
  elapsedTime?: number
  itemStatus?: ItemStatus
  successCount?: number
  failedCount?: number
  failedFiles?: Array<{
    filename: string
    error: string
  }>
  selectedModes?: Mode[]
  onDownload?: (mode?: Mode) => void
  onReset?: () => void
}

export function ProgressDisplay({
  current,
  total,
  status,
  message,
  elapsedTime,
  itemStatus,
  successCount,
  failedCount,
  failedFiles,
  selectedModes = [],
  onDownload,
  onReset,
}: ProgressDisplayProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0

  const formatElapsedTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (mins > 0) {
      return `${mins}m ${secs}s`
    }
    return `${secs}s`
  }

  const calculateEstimatedTime = (): string | null => {
    if (!elapsedTime || current === 0 || total === 0 || status !== "processing") return null

    const avgTimePerFile = elapsedTime / current
    const remainingFiles = total - current
    const estimatedSeconds = avgTimePerFile * remainingFiles

    if (estimatedSeconds < 60) {
      return `~${Math.ceil(estimatedSeconds)}s remaining`
    }

    const mins = Math.floor(estimatedSeconds / 60)
    const secs = Math.ceil(estimatedSeconds % 60)
    return `~${mins}m ${secs}s remaining`
  }

  const getItemStatus = (index: number) => {
    if (index < current) return "success"
    if (index === current) return itemStatus || "processing"
    return "pending"
  }

  if (status === "idle") return null

  const estimatedTime = calculateEstimatedTime()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Processing Status</CardTitle>
          {status === "processing" && (
            <Badge variant="secondary">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              Processing
            </Badge>
          )}
          {status === "completed" && (
            <Badge variant="default" className="bg-green-600">
              <Check className="mr-1 h-3 w-3" />
              Completed
            </Badge>
          )}
          {status === "error" && (
            <Badge variant="destructive">
              <XCircle className="mr-1 h-3 w-3" />
              Error
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        {status === "processing" && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Processing files...</span>
              <span>
                {current} / {total}
              </span>
            </div>
            <Progress value={percentage} className="h-2" />
            <div className="flex items-center justify-between">
              {elapsedTime !== undefined && (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>Elapsed: {formatElapsedTime(elapsedTime)}</span>
                </div>
              )}
              {estimatedTime && (
                <div className="text-xs text-muted-foreground">
                  {estimatedTime}
                </div>
              )}
            </div>

            {/* File Status Indicators */}
            {total > 0 && total <= 20 && (
              <div className="grid grid-cols-10 gap-1.5 pt-2">
                {Array.from({ length: total }).map((_, i) => {
                  const fileStatus = getItemStatus(i + 1)
                  return (
                    <div
                      key={i}
                      className={`w-full h-2 rounded-full transition-all ${
                        fileStatus === "success"
                          ? "bg-green-500"
                          : fileStatus === "error"
                          ? "bg-red-500"
                          : fileStatus === "processing"
                          ? "bg-blue-500 animate-pulse"
                          : "bg-gray-300"
                      }`}
                      title={`File ${i + 1}: ${fileStatus}`}
                    />
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Status Message */}
        <div className="space-y-2">
          <div className="flex items-start gap-2 text-sm">
            <FileText className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
            <p className="text-muted-foreground">{message}</p>
          </div>
          {(status === "completed" || status === "error") && elapsedTime !== undefined && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>Total time: {formatElapsedTime(elapsedTime)}</span>
            </div>
          )}
        </div>

        {/* Failed Files List */}
        {failedFiles && failedFiles.length > 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-900 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <h3 className="font-semibold text-red-800 dark:text-red-300">Failed Files:</h3>
            </div>
            <ul className="space-y-1 text-sm text-red-700 dark:text-red-400">
              {failedFiles.map((file, i) => (
                <li key={i} className="flex items-start gap-2">
                  <XCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="font-medium">{file.filename}</span>
                    <span className="text-red-600 dark:text-red-400">: {file.error}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Success Summary */}
        {status === "completed" && (successCount !== undefined || failedCount !== undefined) && (
          <div className="rounded-lg border border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-900 p-4">
            <div className="flex items-center gap-2 text-green-800 dark:text-green-300">
              <Check className="h-4 w-4" />
              <p className="font-medium">
                Successfully processed {successCount || 0} file{(successCount || 0) !== 1 ? 's' : ''}
                {failedCount !== undefined && failedCount > 0 && ` (${failedCount} failed)`}
              </p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {status === "completed" && onDownload && (
          <div className="pt-2 space-y-2">
            {selectedModes.length > 1 ? (
              <>
                {selectedModes.includes("everything") && (
                  <Button onClick={() => onDownload("everything")} className="w-full">
                    Download Everything Mode
                  </Button>
                )}
                {selectedModes.includes("minimal") && (
                  <Button onClick={() => onDownload("minimal")} variant="outline" className="w-full">
                    Download Minimal Mode
                  </Button>
                )}
              </>
            ) : (
              <Button onClick={() => onDownload(selectedModes[0])} className="w-full">
                Download Excel
              </Button>
            )}
            {onReset && (
              <Button onClick={onReset} variant="secondary" className="w-full">
                Process More Files
              </Button>
            )}
          </div>
        )}

        {/* Reset Button for Error State */}
        {status === "error" && onReset && (
          <div className="pt-2">
            <Button onClick={onReset} variant="secondary" className="w-full">
              Try Again
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
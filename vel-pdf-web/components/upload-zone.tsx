"use client"

import { useState, useCallback } from "react"
import { Upload, FileText, Archive } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
  onValidationError?: (error: string) => void
  compact?: boolean
}

export function UploadZone({ onFilesSelected, disabled, onValidationError, compact = false }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)

  const validateFiles = (files: File[]): File[] => {
    const validFiles: File[] = []
    const invalidFiles: string[] = []

    files.forEach((file) => {
      const isPDF = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
      const isZIP = file.type === "application/zip" || file.type === "application/x-zip-compressed" || file.name.toLowerCase().endsWith(".zip")

      if (isPDF || isZIP) {
        validFiles.push(file)
      } else {
        invalidFiles.push(file.name)
      }
    })

    if (invalidFiles.length > 0) {
      const error = `Invalid file type(s): ${invalidFiles.join(", ")}. Only PDF and ZIP files are allowed.`
      onValidationError?.(error)
    }

    return validFiles
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true)
    }
  }, [])

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      if (disabled) return

      const files = Array.from(e.dataTransfer.files)
      const validFiles = validateFiles(files)

      if (validFiles.length > 0) {
        onFilesSelected(validFiles)
      }
    },
    [onFilesSelected, disabled, validateFiles]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        const files = Array.from(e.target.files)
        const validFiles = validateFiles(files)

        if (validFiles.length > 0) {
          onFilesSelected(validFiles)
        }
      }
    },
    [onFilesSelected, validateFiles]
  )

  return (
    <Card
      className={cn(
        "border-2 border-dashed transition-all duration-200 cursor-pointer",
        isDragging
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-primary/50",
        disabled && "opacity-50 cursor-not-allowed"
      )}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => !disabled && document.getElementById("file-input")?.click()}
    >
      <CardContent className={cn(
        "flex flex-col items-center justify-center px-6",
        compact ? "py-6" : "py-12"
      )}>
        <div className={cn(
          "rounded-full bg-primary/10 mb-4",
          compact ? "p-3" : "p-4"
        )}>
          <Upload className={cn(
            "text-primary",
            compact ? "h-6 w-6" : "h-8 w-8"
          )} />
        </div>
        <h3 className={cn(
          "font-semibold mb-2",
          compact ? "text-base" : "text-xl"
        )}>
          {isDragging ? "Drop files here" : compact ? "Add More Files" : "Upload PDF Files"}
        </h3>
        {!compact && (
          <p className="text-sm text-muted-foreground text-center mb-4">
            Drag and drop your files here, or click to browse
          </p>
        )}
        <div className="flex gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            <span>PDF</span>
          </div>
          <div className="flex items-center gap-1">
            <Archive className="h-4 w-4" />
            <span>ZIP</span>
          </div>
        </div>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.zip"
          className="hidden"
          onChange={handleFileInput}
          disabled={disabled}
        />
      </CardContent>
    </Card>
  )
}
'use client'

import { FileText, X, Check, Loader2, AlertCircle, Archive } from 'lucide-react'
import { Card, CardContent } from './ui/card'
import { Button } from './ui/button'
import { cn } from '@/lib/utils'

interface FileListPanelProps {
  files: File[]
  onRemoveFile?: (index: number) => void
  currentProcessingIndex?: number
  fileStatuses?: Map<number, 'pending' | 'processing' | 'success' | 'error'>
  disabled?: boolean
}

export function FileListPanel({
  files,
  onRemoveFile,
  currentProcessingIndex,
  fileStatuses = new Map(),
  disabled = false,
}: FileListPanelProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (file: File) => {
    if (file.name.toLowerCase().endsWith('.zip')) {
      return <Archive className="h-5 w-5 text-blue-500" />
    }
    return <FileText className="h-5 w-5 text-gray-600 dark:text-gray-400" />
  }

  const getStatusIcon = (index: number) => {
    const status = fileStatuses.get(index) || 'pending'

    switch (status) {
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'success':
        return <Check className="h-4 w-4 text-green-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
    }
  }

  if (files.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground">No files selected</p>
          <p className="text-xs text-muted-foreground mt-1">
            Upload files to see them here
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm text-muted-foreground">
          Selected Files ({files.length})
        </h3>
      </div>

      <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
        {files.map((file, index) => {
          const isProcessing = currentProcessingIndex === index
          const status = fileStatuses.get(index) || 'pending'

          return (
            <Card
              key={index}
              className={cn(
                'transition-all duration-200',
                isProcessing && 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-950/20',
                status === 'success' && 'bg-green-50 dark:bg-green-950/20',
                status === 'error' && 'bg-red-50 dark:bg-red-950/20'
              )}
            >
              <CardContent className="p-3">
                <div className="flex items-start gap-3">
                  {/* File Icon */}
                  <div className="mt-0.5">{getFileIcon(file)}</div>

                  {/* File Details */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center gap-2">
                    {getStatusIcon(index)}
                    {onRemoveFile && !disabled && status === 'pending' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => onRemoveFile(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

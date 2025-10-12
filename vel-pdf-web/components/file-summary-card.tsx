'use client'

import { Files, HardDrive } from 'lucide-react'
import { Card, CardContent } from './ui/card'

interface FileSummaryCardProps {
  fileCount: number
  totalSize: number
}

export function FileSummaryCard({ fileCount, totalSize }: FileSummaryCardProps) {
  const formatTotalSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Files className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Total Files</span>
            </div>
            <span className="text-sm font-semibold">{fileCount}</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Total Size</span>
            </div>
            <span className="text-sm font-semibold">{formatTotalSize(totalSize)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

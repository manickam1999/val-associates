import { logger } from './logger'

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

export interface UploadResponse {
  session_id: string
  message: string
  total_files: number
}

export type ProgressStatus = "idle" | "processing" | "completed" | "error"
export type ItemStatus = "processing" | "success" | "error"

export interface ProgressMessage {
  current: number
  total: number
  status: ProgressStatus
  message: string
  item_status?: ItemStatus
  elapsed_time?: number
  success_count?: number
  failed_count?: number
  failed_files?: Array<{
    filename: string
    error: string
  }>
}

export async function uploadFiles(
  files: File[],
  onProgress?: (loaded: number, total: number) => void
): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append("files", file)
  })

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    // Track upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(event.loaded, event.total)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText)
          resolve(response)
        } catch {
          reject(new Error('Invalid response from server'))
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed: Network error'))
    })

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled'))
    })

    xhr.open('POST', `${API_URL}/api/upload`)
    xhr.send(formData)
  })
}

export function connectWebSocket(
  sessionId: string,
  modes: string[],
  onMessage: (message: ProgressMessage) => void,
  onError: (error: Event) => void,
  onClose?: (event: CloseEvent) => void,
  onOpen?: () => void
): WebSocket {
  const modesParam = modes.join(',')
  const wsUrl = `${WS_URL}/ws/progress/${sessionId}?modes=${modesParam}`
  logger.log('🔌 Connecting to WebSocket:', wsUrl)
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    logger.log('✅ WebSocket connected successfully')
    onOpen?.()
  }

  ws.onmessage = (event) => {
    logger.log('📦 Raw WebSocket data:', event.data)
    const data = JSON.parse(event.data)
    onMessage(data)

    // Send acknowledgment when processing completes
    if (data.status === 'completed' || data.status === 'error') {
      logger.log('✅ Sending acknowledgment')
      ws.send('ack')
    }
  }

  ws.onerror = (error) => {
    logger.error('❌ WebSocket error:', error)
    onError(error)
  }

  ws.onclose = (event) => {
    logger.log(`🔌 WebSocket closed. Clean: ${event.wasClean}, Code: ${event.code}, Reason: ${event.reason}`)
    if (!event.wasClean) {
      logger.warn('⚠️ WebSocket connection closed unexpectedly')
    }
    onClose?.(event)
  }

  return ws
}

export function downloadExcel(sessionId: string, mode?: string): void {
  const downloadUrl = mode
    ? `${API_URL}/api/download/${sessionId}?mode=${mode}`
    : `${API_URL}/api/download/${sessionId}`
  window.open(downloadUrl, "_blank")
}
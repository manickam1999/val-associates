'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { uploadFiles, connectWebSocket, type ProgressMessage } from '@/lib/api-client'
import { logger } from '@/lib/logger'

export function useFileProcessing() {
  const [progress, setProgress] = useState<ProgressMessage>({
    current: 0,
    total: 0,
    status: 'idle',
    message: '',
  })
  const [isProcessing, setIsProcessing] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 3

  // Cleanup on unmount
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

  const connectToWebSocket = useCallback((sid: string, totalFiles: number, modes: string[]) => {
    const ws = connectWebSocket(
      sid,
      modes,
      (message) => {
        logger.log('📨 WebSocket message received:', message)
        logger.log(`Progress: ${message.current}/${message.total} (${message.current && message.total ? Math.round((message.current / message.total) * 100) : 0}%)`)
        setProgress(message)
        if (message.status === 'completed' || message.status === 'error') {
          reconnectAttemptsRef.current = 0
          setWsConnected(false)
          setIsProcessing(false)
          ws.close()
        }
      },
      (error) => {
        logger.error('WebSocket error:', error)
        setWsConnected(false)
        setProgress({
          current: 0,
          total: 0,
          status: 'error',
          message: 'Connection error. Please try again.',
        })
        setIsProcessing(false)
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
            connectToWebSocket(sid, totalFiles, modes)
          }, 2000)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setProgress({
            current: 0,
            total: 0,
            status: 'error',
            message: 'Failed to reconnect. Please try again.',
          })
          setIsProcessing(false)
        }
      },
      () => {
        // Handle connection open
        setWsConnected(true)
      }
    )

    wsRef.current = ws
  }, [])

  const processFiles = useCallback(async (files: File[], modes: string[]) => {
    if (files.length === 0) return

    setIsProcessing(true)
    reconnectAttemptsRef.current = 0

    // Show initial loading state
    setProgress({
      current: 0,
      total: files.length,
      status: 'processing',
      message: 'Uploading files to server...',
    })

    try {
      // Upload files
      const response = await uploadFiles(files)
      setSessionId(response.session_id)

      // Update to processing state
      setProgress({
        current: 0,
        total: response.total_files,
        status: 'processing',
        message: 'Connecting to server...',
      })

      // Connect to WebSocket for progress
      connectToWebSocket(response.session_id, response.total_files, modes)
      setIsProcessing(false)

      return response.session_id
    } catch (error) {
      logger.error('Upload error:', error)
      setProgress({
        current: 0,
        total: 0,
        status: 'error',
        message: error instanceof Error ? error.message : 'Upload failed. Please try again.',
      })
      setIsProcessing(false)
    }
  }, [connectToWebSocket])

  const reset = useCallback(() => {
    setProgress({
      current: 0,
      total: 0,
      status: 'idle',
      message: '',
    })
    setSessionId('')
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  return {
    progress,
    isProcessing,
    wsConnected,
    sessionId,
    processFiles,
    reset,
  }
}

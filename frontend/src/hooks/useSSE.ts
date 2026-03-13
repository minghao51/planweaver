import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE } from '../api/client';

interface SSEEvents {
  onConnected?: (data: { session_id: string }) => void;
  onStepCompleted?: (data: {
    step_id: number;
    task: string;
    output: string;
  }) => void;
  onStepFailed?: (data: { step_id: number; error: string }) => void;
  onExecutionComplete?: (data: {
    total_steps: number;
    completed: number;
  }) => void;
  onExecutionFailed?: (data: { reason: string }) => void;
  onError?: (data: { message: string }) => void;
}

export function useSSE(sessionId: string, events: SSEEvents = {}) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsRef = useRef(events);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  useEffect(() => {
    if (!sessionId) return;

    const configuredBase = import.meta.env.VITE_API_BASE || API_BASE;
    const streamUrl = new URL(
      `${configuredBase.replace(/\/$/, '')}/sessions/${sessionId}/stream`,
      window.location.origin
    ).toString();
    const eventSource = new EventSource(streamUrl);

    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      setConnected(false);
      setError('Connection error');
      events.onError?.({ message: 'Connection error' });
    };

    // Listen for connected event
    eventSource.addEventListener('connected', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        eventsRef.current.onConnected?.(data);
      } catch (err) {
        console.error('Failed to parse connected event:', err);
      }
    });

    // Listen for step_completed events
    eventSource.addEventListener('step_completed', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        eventsRef.current.onStepCompleted?.(data);
      } catch (err) {
        console.error('Failed to parse step_completed event:', err);
      }
    });

    // Listen for step_failed events
    eventSource.addEventListener('step_failed', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        eventsRef.current.onStepFailed?.(data);
      } catch (err) {
        console.error('Failed to parse step_failed event:', err);
      }
    });

    // Listen for execution_complete events
    eventSource.addEventListener('execution_complete', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        eventsRef.current.onExecutionComplete?.(data);
      } catch (err) {
        console.error('Failed to parse execution_complete event:', err);
      }
    });

    // Listen for execution_failed events
    eventSource.addEventListener('execution_failed', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        eventsRef.current.onExecutionFailed?.(data);
      } catch (err) {
        console.error('Failed to parse execution_failed event:', err);
      }
    });

    // Listen for error events
    eventSource.addEventListener('error', (e: MessageEvent) => {
      if (!e.data) {
        return;
      }
      try {
        const data = JSON.parse(e.data);
        setError(data.message);
        eventsRef.current.onError?.(data);
      } catch (err) {
        console.error('Failed to parse error event:', err);
      }
    });

    // Cleanup on unmount
    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setConnected(false);
    };
  }, [sessionId]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
  }, []);

  return {
    connected,
    error,
    disconnect,
  };
}

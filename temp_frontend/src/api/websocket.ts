import { useEffect, useRef } from 'react';
const base = import.meta.env.VITE_WS_URL;

interface WSMessage {
  type?: string;
  event?: string;
  data?: Record<string, unknown>;
  [key: string]: unknown;
}

export function useWebSocket(
  repoId: number | null,
  onMessage: (msg: WSMessage) => void,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const closedIntentionally = useRef(false);

  // Keep callback ref updated without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (repoId == null) return;

    closedIntentionally.current = false;

    function connect() {
      if (closedIntentionally.current) return;


      const ws = new WebSocket(
        `${base}/realtime/ws/${repoId}`
      );

      ws.onmessage = (ev) => {
        try {
          const msg: WSMessage = JSON.parse(ev.data);
          onMessageRef.current(msg);
        } catch { /* ignore parse errors */ }
      };
      ws.onerror = (e) => {
        console.log("WS error", e);
      };


      ws.onclose = (e) => {
        if (!closedIntentionally.current) {
          console.log("WS closed", e.code, e.reason);
          wsRef.current = null;
          setTimeout(connect, 3000);
        }
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      closedIntentionally.current = true;
      wsRef.current?.close();
    };
  }, [repoId]);
}

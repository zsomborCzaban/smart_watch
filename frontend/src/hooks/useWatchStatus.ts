import { useEffect, useState } from "react";
import type { HikingSession } from "../types";

export function useWatchStatus(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [activeSession, setActiveSession] = useState<HikingSession | null>(null);
  const isActiveSession = activeSession !== null;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      ws = new WebSocket(url);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("Received WebSocket message:", data);
          if (typeof data.type === "string") {
            if (data.type === "session_update") {
              if(data.isActive === true){
                setActiveSession(data);
              }else{
                setActiveSession(null);
              }
              setIsConnected(data.connected);
            }
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [url]);

  return { isConnected, activeSession, isActiveSession };
}

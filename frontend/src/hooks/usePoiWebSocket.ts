import { useEffect, useRef, useState } from "react";
import type { PoiSummary } from "../types";
import { POIS_WS_URL } from "../config";

export function usePoiWebSocket(
  initialPois: PoiSummary[],
): PoiSummary[] {
  const [pois, setPois] = useState<PoiSummary[]>(initialPois);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setPois(initialPois);
  }, [initialPois]);

  useEffect(() => {
    const ws = new WebSocket(POIS_WS_URL);
    wsRef.current = ws;

    ws.onmessage = (event: MessageEvent<string>) => {
      const data: PoiSummary[] = JSON.parse(event.data) as PoiSummary[];
      setPois(data);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);

  return pois;
}

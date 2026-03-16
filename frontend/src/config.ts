const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const WS_BASE = import.meta.env.VITE_WS_BASE ?? "ws://localhost:8000";

export const API_URL = `${API_BASE}/api`;
export const WS_URL = `${WS_BASE}/ws`;
export const POIS_API_URL = `${API_URL}/pois`;
export const POIS_WS_URL = `${WS_URL}/pois`;

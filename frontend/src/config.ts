const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const WS_BASE =
  import.meta.env.VITE_WS_BASE ??
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export const API_URL = `${API_BASE}/api`;
export const WS_URL = `${WS_BASE}/ws`;
export const POIS_API_URL = `${API_URL}/pois`;
export const POIS_WS_URL = `${WS_URL}/pois`;

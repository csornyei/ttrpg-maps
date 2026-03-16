import type { PoiDetail, PoiSummary } from "./types";
import { POIS_API_URL } from "./config";

export async function fetchPois(): Promise<PoiSummary[]> {
  const response = await fetch(POIS_API_URL);
  if (!response.ok) {
    throw new Error(`Failed to fetch PoIs: ${response.status}`);
  }
  return response.json() as Promise<PoiSummary[]>;
}

export async function fetchPoiDetail(id: string): Promise<PoiDetail> {
  const response = await fetch(`${POIS_API_URL}/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch PoI detail: ${response.status}`);
  }
  return response.json() as Promise<PoiDetail>;
}

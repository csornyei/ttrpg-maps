export interface PoiSummary {
  id: string;
  name: string;
  col: number;
  row: number;
  color: string;
}

export interface PoiDetail extends PoiSummary {
  description: string;
  notes: string;
}

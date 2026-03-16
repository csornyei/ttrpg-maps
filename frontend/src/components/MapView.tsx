import { useMemo } from "react";
import type { PoiSummary } from "../types";
import { PoiMarker } from "./PoiMarker";
import { deriveHexSize, hexToPixel } from "../hexUtils";
import mapImage from "../assets/echo_valley.png";

const MAP_WIDTH = 2815;
const MAP_HEIGHT = 2418;

interface MapViewProps {
  pois: PoiSummary[];
  onPoiClick: (id: string) => void;
}

export function MapView({ pois, onPoiClick }: MapViewProps) {
  const hexSize = useMemo(() => deriveHexSize(MAP_WIDTH, MAP_HEIGHT), []);

  return (
    <div className="map-container">
      <img
        src={mapImage}
        alt="Echo Valley Map"
        className="map-image"
        style={{ width: "100%", height: "auto", display: "block" }}
      />
      <svg
        className="map-overlay"
        width="100%"
        height="100%"
        viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        preserveAspectRatio="xMinYMin meet"
      >
        {pois.map((poi) => {
          const pos = hexToPixel(poi.col, poi.row, hexSize);
          return (
            <PoiMarker
              key={poi.id}
              id={poi.id}
              name={poi.name}
              color={poi.color}
              pixelX={pos.x}
              pixelY={pos.y}
              onClick={onPoiClick}
            />
          );
        })}
      </svg>
    </div>
  );
}

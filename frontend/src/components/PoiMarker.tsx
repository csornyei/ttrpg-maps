interface PoiMarkerProps {
  id: string;
  name: string;
  color: string;
  pixelX: number;
  pixelY: number;
  onClick: (id: string) => void;
}

const OUTER_RADIUS = 28;
const INNER_RADIUS = 14;

export function PoiMarker({
  id,
  name,
  color,
  pixelX,
  pixelY,
  onClick,
}: PoiMarkerProps) {
  const handleClick = () => {
    onClick(id);
  };

  return (
    <g
      transform={`translate(${pixelX}, ${pixelY})`}
      onClick={handleClick}
      style={{ cursor: "pointer" }}
    >
      <circle r={OUTER_RADIUS} fill={color} opacity={0.4} />
      <circle r={INNER_RADIUS} fill={color} />
      <title>{name}</title>
    </g>
  );
}

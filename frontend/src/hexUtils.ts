export interface PixelPosition {
  x: number;
  y: number;
}

export interface HexGridConfig {
  hexSize: number;
}

const HEX_COLS = 36;
const HEX_ROWS = 36;
const SQRT3 = Math.sqrt(3);

export function deriveHexSize(imageWidth: number, imageHeight: number): number {
  const fromWidth = imageWidth / ((HEX_COLS + 0.5) * SQRT3);
  const fromHeight = imageHeight / (1.5 * HEX_ROWS + 0.5);
  return (fromWidth + fromHeight) / 2;
}

export function hexToPixel(
  col: number,
  row: number,
  hexSize: number,
): PixelPosition {
  const x = hexSize * SQRT3 * (col + 0.5 * (row & 1)) + (SQRT3 * hexSize) / 2;
  const y = hexSize * 1.5 * row + hexSize;
  return { x, y };
}

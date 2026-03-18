import { describe, it, expect } from 'vitest'
import { deriveHexSize, hexToPixel } from './hexUtils'

const SQRT3 = Math.sqrt(3)

describe('deriveHexSize', () => {
  it('returns ~44.5 for the actual map dimensions', () => {
    const size = deriveHexSize(2815, 2418)
    expect(size).toBeCloseTo(44.5, 0)
  })

  it('returns a positive number for positive dimensions', () => {
    expect(deriveHexSize(1000, 800)).toBeGreaterThan(0)
  })

  it('returns positive for a landscape image', () => {
    expect(deriveHexSize(3000, 1000)).toBeGreaterThan(0)
  })

  it('returns positive for a portrait image', () => {
    expect(deriveHexSize(1000, 3000)).toBeGreaterThan(0)
  })

  it('returns a consistent value when both dimensions are equal', () => {
    const a = deriveHexSize(1000, 1000)
    const b = deriveHexSize(1000, 1000)
    expect(a).toBe(b)
    expect(a).toBeGreaterThan(0)
  })
})

describe('hexToPixel', () => {
  it('col=0 row=0 returns { x: √3*hexSize/2, y: hexSize }', () => {
    const hexSize = 44
    const pos = hexToPixel(0, 0, hexSize)
    // x = hexSize*√3*(0 + 0) + √3*hexSize/2 = √3*hexSize/2
    expect(pos.x).toBeCloseTo((SQRT3 * hexSize) / 2)
    expect(pos.y).toBeCloseTo(hexSize)
  })

  it('even row has no parity offset', () => {
    const hexSize = 50
    const evenRow = hexToPixel(2, 0, hexSize)
    const expectedX = hexSize * SQRT3 * (2 + 0) + (SQRT3 * hexSize) / 2
    expect(evenRow.x).toBeCloseTo(expectedX)
  })

  it('odd row has half-hex parity offset', () => {
    const hexSize = 50
    const oddRow = hexToPixel(2, 1, hexSize)
    const expectedX = hexSize * SQRT3 * (2 + 0.5) + (SQRT3 * hexSize) / 2
    expect(oddRow.x).toBeCloseTo(expectedX)
  })

  it('larger hexSize scales x and y proportionally', () => {
    const small = hexToPixel(3, 2, 10)
    const large = hexToPixel(3, 2, 20)
    expect(large.x).toBeCloseTo(small.x * 2)
    expect(large.y).toBeCloseTo(small.y * 2)
  })

  it('matches hand-calculated values for col=1, row=2, hexSize=40', () => {
    const hexSize = 40
    const pos = hexToPixel(1, 2, hexSize)
    const expectedX = hexSize * SQRT3 * (1 + 0.5 * (2 & 1)) + (SQRT3 * hexSize) / 2
    const expectedY = hexSize * 1.5 * 2 + hexSize
    expect(pos.x).toBeCloseTo(expectedX)
    expect(pos.y).toBeCloseTo(expectedY)
  })
})

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MapView } from './MapView'
import { deriveHexSize, hexToPixel } from '../hexUtils'
import type { PoiSummary } from '../types'

vi.mock('../assets/echo_valley.png', () => ({ default: 'map.png' }))

const MAP_WIDTH = 2815
const MAP_HEIGHT = 2418

const makePoi = (id: string, col: number, row: number): PoiSummary => ({
  id,
  name: `POI ${id}`,
  col,
  row,
  color: '#ff0000',
})

describe('MapView rendering', () => {
  it('renders the map image', () => {
    render(<MapView pois={[]} onPoiClick={vi.fn()} />)
    expect(screen.getByAltText('Echo Valley Map')).toBeInTheDocument()
  })

  it('renders an svg overlay', () => {
    const { container } = render(<MapView pois={[]} onPoiClick={vi.fn()} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders no marker groups when pois is empty', () => {
    const { container } = render(<MapView pois={[]} onPoiClick={vi.fn()} />)
    expect(container.querySelectorAll('svg g')).toHaveLength(0)
  })

  it('renders one group per poi', () => {
    const pois = [makePoi('a', 0, 0), makePoi('b', 1, 0), makePoi('c', 2, 1)]
    const { container } = render(<MapView pois={pois} onPoiClick={vi.fn()} />)
    expect(container.querySelectorAll('svg g')).toHaveLength(3)
  })
})

describe('MapView marker positioning', () => {
  it('marker for col=0, row=0 has correct translate transform', () => {
    const pois = [makePoi('x', 0, 0)]
    const { container } = render(<MapView pois={pois} onPoiClick={vi.fn()} />)
    const hexSize = deriveHexSize(MAP_WIDTH, MAP_HEIGHT)
    const { x, y } = hexToPixel(0, 0, hexSize)
    const g = container.querySelector('svg g')!
    expect(g).toHaveAttribute('transform', `translate(${x}, ${y})`)
  })
})

describe('MapView interaction', () => {
  it('clicking a marker calls onPoiClick with the correct id', async () => {
    const onPoiClick = vi.fn()
    const pois = [makePoi('poi-1', 0, 0)]
    const { container } = render(<MapView pois={pois} onPoiClick={onPoiClick} />)
    const g = container.querySelector('svg g')!
    await userEvent.click(g)
    expect(onPoiClick).toHaveBeenCalledWith('poi-1')
  })

  it('each marker is independently clickable', async () => {
    const onPoiClick = vi.fn()
    const pois = [makePoi('a', 0, 0), makePoi('b', 5, 5)]
    const { container } = render(<MapView pois={pois} onPoiClick={onPoiClick} />)
    const groups = container.querySelectorAll('svg g')
    await userEvent.click(groups[1])
    expect(onPoiClick).toHaveBeenCalledWith('b')
    expect(onPoiClick).toHaveBeenCalledTimes(1)
  })
})

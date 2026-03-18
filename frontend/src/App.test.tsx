import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MockWebSocket } from './test/mocks/MockWebSocket'
import type { PoiDetail, PoiSummary } from './types'

vi.mock('./api', () => ({
  fetchPois: vi.fn(),
  fetchPoiDetail: vi.fn(),
}))
vi.mock('./assets/echo_valley.png', () => ({ default: 'map.png' }))

import { fetchPois, fetchPoiDetail } from './api'
import App from './App'

const mockFetchPois = vi.mocked(fetchPois)
const mockFetchPoiDetail = vi.mocked(fetchPoiDetail)

const poi: PoiSummary = { id: 'p1', name: 'The Ruins', col: 2, row: 3, color: '#aa0000' }
const detail: PoiDetail = { ...poi, description: 'Old ruins.', notes: 'Beware the traps.' }

beforeEach(() => {
  vi.stubGlobal('WebSocket', MockWebSocket)
  mockFetchPois.mockResolvedValue([poi])
  mockFetchPoiDetail.mockResolvedValue(detail)
})

afterEach(() => {
  vi.clearAllMocks()
  vi.unstubAllGlobals()
})

describe('App initial render', () => {
  it('shows the page heading', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Daggerheart Map')
  })

  it('calls fetchPois once on mount', async () => {
    render(<App />)
    await waitFor(() => expect(mockFetchPois).toHaveBeenCalledOnce())
  })

  it('renders poi markers after fetchPois resolves', async () => {
    const { container } = render(<App />)
    await waitFor(() => {
      expect(container.querySelectorAll('svg g')).toHaveLength(1)
    })
  })
})

describe('App POI click → drawer opens', () => {
  it('calls fetchPoiDetail with poi id', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => expect(mockFetchPoiDetail).toHaveBeenCalledWith('p1'))
  })

  it('drawer gains drawer--open class', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => {
      expect(container.querySelector('.drawer')).toHaveClass('drawer--open')
    })
  })

  it('drawer shows detail name and description', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'The Ruins' })).toBeInTheDocument()
      expect(screen.getByText('Old ruins.')).toBeInTheDocument()
    })
  })
})

describe('App drawer close', () => {
  it('removes drawer--open when close button is clicked', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => expect(container.querySelector('.drawer--open')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button'))
    expect(container.querySelector('.drawer--open')).not.toBeInTheDocument()
  })
})

describe('App main scroll padding', () => {
  it('adds app__main--drawer-open class to main when drawer opens', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => {
      expect(container.querySelector('main')).toHaveClass('app__main--drawer-open')
    })
  })

  it('removes app__main--drawer-open class when drawer closes', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => expect(container.querySelector('.drawer--open')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button'))
    expect(container.querySelector('main')).not.toHaveClass('app__main--drawer-open')
  })
})

describe('App WebSocket updates', () => {
  it('updates markers when WebSocket sends a new poi list', async () => {
    const newPoi: PoiSummary = { id: 'p2', name: 'New Place', col: 5, row: 5, color: '#00ff00' }
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    act(() => {
      MockWebSocket.instance.simulateMessage([poi, newPoi])
    })
    await waitFor(() => {
      expect(container.querySelectorAll('svg g')).toHaveLength(2)
    })
  })
})

describe('App error handling', () => {
  it('renders without crashing when fetchPois rejects', async () => {
    mockFetchPois.mockRejectedValue(new Error('network error'))
    render(<App />)
    await waitFor(() => expect(mockFetchPois).toHaveBeenCalled())
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('drawer does not open when fetchPoiDetail rejects', async () => {
    mockFetchPoiDetail.mockRejectedValue(new Error('not found'))
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('svg g')).toHaveLength(1))
    await userEvent.click(container.querySelector('svg g')!)
    await waitFor(() => expect(mockFetchPoiDetail).toHaveBeenCalled())
    expect(container.querySelector('.drawer--open')).not.toBeInTheDocument()
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePoiWebSocket } from './usePoiWebSocket'
import { MockWebSocket } from '../test/mocks/MockWebSocket'
import { POIS_WS_URL } from '../config'
import type { PoiSummary } from '../types'

const poi = (id: string): PoiSummary => ({ id, name: id, col: 0, row: 0, color: '#fff' })
const NO_POIS: PoiSummary[] = []

beforeEach(() => {
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('usePoiWebSocket initial state', () => {
  it('returns initialPois before any message', () => {
    const initial = [poi('a'), poi('b')]
    const { result } = renderHook(() => usePoiWebSocket(initial))
    expect(result.current).toEqual(initial)
  })
})

describe('usePoiWebSocket prop sync', () => {
  it('updates when initialPois prop changes', () => {
    let initial = [poi('a')]
    const { result, rerender } = renderHook(() => usePoiWebSocket(initial))
    expect(result.current).toEqual([poi('a')])

    initial = [poi('a'), poi('b')]
    rerender()
    expect(result.current).toEqual([poi('a'), poi('b')])
  })
})

describe('usePoiWebSocket lifecycle', () => {
  it('creates a WebSocket with POIS_WS_URL on mount', () => {
    renderHook(() => usePoiWebSocket(NO_POIS))
    expect(MockWebSocket.instance.url).toBe(POIS_WS_URL)
  })

  it('calls ws.close() on unmount', () => {
    const { unmount } = renderHook(() => usePoiWebSocket(NO_POIS))
    const ws = MockWebSocket.instance
    unmount()
    expect(ws.close).toHaveBeenCalledOnce()
  })
})

describe('usePoiWebSocket message handling', () => {
  it('updates pois when a message is received', () => {
    const { result } = renderHook(() => usePoiWebSocket(NO_POIS))
    act(() => {
      MockWebSocket.instance.simulateMessage([poi('x')])
    })
    expect(result.current).toEqual([poi('x')])
  })

  it('subsequent messages overwrite previous state', () => {
    const { result } = renderHook(() => usePoiWebSocket(NO_POIS))
    act(() => { MockWebSocket.instance.simulateMessage([poi('x')]) })
    act(() => { MockWebSocket.instance.simulateMessage([poi('y')]) })
    expect(result.current).toEqual([poi('y')])
  })

  it('multiple pois in one message all appear in result', () => {
    const { result } = renderHook(() => usePoiWebSocket(NO_POIS))
    act(() => {
      MockWebSocket.instance.simulateMessage([poi('a'), poi('b'), poi('c')])
    })
    expect(result.current).toHaveLength(3)
  })
})

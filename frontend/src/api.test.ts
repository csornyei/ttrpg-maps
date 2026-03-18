import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchPois, fetchPoiDetail } from './api'
import { POIS_API_URL } from './config'

function mockFetch(ok: boolean, status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchPois', () => {
  it('makes a GET request to POIS_API_URL', async () => {
    const fake = mockFetch(true, 200, [])
    vi.stubGlobal('fetch', fake)
    await fetchPois()
    expect(fake).toHaveBeenCalledWith(POIS_API_URL)
  })

  it('returns parsed JSON on 200', async () => {
    const data = [{ id: '1', name: 'A', col: 0, row: 0, color: '#fff' }]
    vi.stubGlobal('fetch', mockFetch(true, 200, data))
    const result = await fetchPois()
    expect(result).toEqual(data)
  })

  it('throws with status 500 when response.ok is false', async () => {
    vi.stubGlobal('fetch', mockFetch(false, 500, null))
    await expect(fetchPois()).rejects.toThrow('Failed to fetch PoIs: 500')
  })

  it('throws with status 404', async () => {
    vi.stubGlobal('fetch', mockFetch(false, 404, null))
    await expect(fetchPois()).rejects.toThrow('Failed to fetch PoIs: 404')
  })
})

describe('fetchPoiDetail', () => {
  it('makes a GET request to POIS_API_URL/:id', async () => {
    const fake = mockFetch(true, 200, {})
    vi.stubGlobal('fetch', fake)
    await fetchPoiDetail('abc')
    expect(fake).toHaveBeenCalledWith(`${POIS_API_URL}/abc`)
  })

  it('returns parsed JSON on 200', async () => {
    const detail = { id: '1', name: 'A', col: 0, row: 0, color: '#fff', description: 'D', notes: 'N' }
    vi.stubGlobal('fetch', mockFetch(true, 200, detail))
    const result = await fetchPoiDetail('1')
    expect(result).toEqual(detail)
  })

  it('throws with status 404 when response.ok is false', async () => {
    vi.stubGlobal('fetch', mockFetch(false, 404, null))
    await expect(fetchPoiDetail('xyz')).rejects.toThrow('Failed to fetch PoI detail: 404')
  })

  it('interpolates the id into the URL', async () => {
    const fake = mockFetch(true, 200, {})
    vi.stubGlobal('fetch', fake)
    await fetchPoiDetail('my-special-id')
    expect(fake).toHaveBeenCalledWith(`${POIS_API_URL}/my-special-id`)
  })
})

import { describe, it, expect, vi, afterEach } from 'vitest'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('config with env vars set', () => {
  it('uses VITE_API_BASE for POIS_API_URL', async () => {
    vi.stubEnv('VITE_API_BASE', 'https://api.example.com')
    vi.resetModules()
    const { POIS_API_URL } = await import('./config')
    expect(POIS_API_URL).toBe('https://api.example.com/api/pois')
  })

  it('uses VITE_WS_BASE for POIS_WS_URL', async () => {
    vi.stubEnv('VITE_WS_BASE', 'wss://api.example.com')
    vi.resetModules()
    const { POIS_WS_URL } = await import('./config')
    expect(POIS_WS_URL).toBe('wss://api.example.com/ws/pois')
  })
})

describe('config without env vars (fallback)', () => {
  it('POIS_API_URL falls back to /api/pois', async () => {
    vi.stubEnv('VITE_API_BASE', '')
    vi.resetModules()
    const { POIS_API_URL } = await import('./config')
    expect(POIS_API_URL).toBe('/api/pois')
  })

  it('WS fallback uses ws:// for http: protocol', async () => {
    // Don't stub VITE_WS_BASE — leave it undefined so ?? fallback triggers
    // jsdom defaults to http://localhost
    vi.resetModules()
    const { POIS_WS_URL } = await import('./config')
    expect(POIS_WS_URL).toMatch(/^ws:\/\//)
  })
})

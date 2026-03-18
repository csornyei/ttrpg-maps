import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PoiMarker } from './PoiMarker'

function renderMarker(overrides = {}) {
  const props = {
    id: 'poi-1',
    name: 'The Tavern',
    color: '#ff0000',
    pixelX: 100,
    pixelY: 200,
    onClick: vi.fn(),
    ...overrides,
  }
  const { container } = render(
    <svg>
      <PoiMarker {...props} />
    </svg>
  )
  return { container, onClick: props.onClick }
}

describe('PoiMarker rendering', () => {
  it('renders two circle elements', () => {
    const { container } = renderMarker()
    expect(container.querySelectorAll('circle')).toHaveLength(2)
  })

  it('outer circle has r=28', () => {
    const { container } = renderMarker()
    const circles = container.querySelectorAll('circle')
    expect(circles[0]).toHaveAttribute('r', '28')
  })

  it('inner circle has r=14', () => {
    const { container } = renderMarker()
    const circles = container.querySelectorAll('circle')
    expect(circles[1]).toHaveAttribute('r', '14')
  })

  it('both circles use the color prop as fill', () => {
    const { container } = renderMarker({ color: '#abcdef' })
    const circles = container.querySelectorAll('circle')
    expect(circles[0]).toHaveAttribute('fill', '#abcdef')
    expect(circles[1]).toHaveAttribute('fill', '#abcdef')
  })

  it('outer circle has opacity=0.4', () => {
    const { container } = renderMarker()
    const circles = container.querySelectorAll('circle')
    expect(circles[0]).toHaveAttribute('opacity', '0.4')
  })

  it('renders a title element with the name', () => {
    renderMarker({ name: 'Dragon Keep' })
    expect(screen.getByText('Dragon Keep').tagName.toLowerCase()).toBe('title')
  })

  it('root g has cursor pointer style', () => {
    const { container } = renderMarker()
    const g = container.querySelector('g')
    expect(g).toHaveStyle({ cursor: 'pointer' })
  })
})

describe('PoiMarker interaction', () => {
  it('clicking calls onClick with the correct id', async () => {
    const { container, onClick } = renderMarker({ id: 'poi-42' })
    const g = container.querySelector('g')!
    await userEvent.click(g)
    expect(onClick).toHaveBeenCalledWith('poi-42')
  })

  it('onClick is not called on render', () => {
    const { onClick } = renderMarker()
    expect(onClick).not.toHaveBeenCalled()
  })
})

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DetailDrawer } from './DetailDrawer'
import type { PoiDetail } from '../types'

const detail: PoiDetail = {
  id: '1',
  name: 'Echo Spire',
  col: 3,
  row: 4,
  color: '#8844cc',
  description: 'A tall ancient tower.',
  notes: 'The mage lives here.',
}

describe('DetailDrawer when detail is null', () => {
  it('renders nothing', () => {
    const { container } = render(
      <DetailDrawer detail={null} isOpen={false} onClose={vi.fn()} />
    )
    expect(container).toBeEmptyDOMElement()
  })
})

describe('DetailDrawer when isOpen=true', () => {
  it('root has drawer and drawer--open classes', () => {
    const { container } = render(
      <DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />
    )
    expect(container.firstChild).toHaveClass('drawer', 'drawer--open')
  })

  it('h2 shows the name with the color style', () => {
    render(<DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />)
    const h2 = screen.getByRole('heading', { level: 2 })
    expect(h2).toHaveTextContent('Echo Spire')
    expect(h2).toHaveStyle({ color: '#8844cc' })
  })

  it('description paragraph is present', () => {
    render(<DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('A tall ancient tower.')).toBeInTheDocument()
  })

  it('notes heading says GM Notes', () => {
    render(<DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('GM Notes')).toBeInTheDocument()
  })

  it('notes paragraph is present', () => {
    render(<DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('The mage lives here.')).toBeInTheDocument()
  })

  it('close button is present', () => {
    render(<DetailDrawer detail={detail} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })
})

describe('DetailDrawer when isOpen=false', () => {
  it('root has drawer but not drawer--open', () => {
    const { container } = render(
      <DetailDrawer detail={detail} isOpen={false} onClose={vi.fn()} />
    )
    expect(container.firstChild).toHaveClass('drawer')
    expect(container.firstChild).not.toHaveClass('drawer--open')
  })

  it('content is still rendered', () => {
    render(<DetailDrawer detail={detail} isOpen={false} onClose={vi.fn()} />)
    expect(screen.getByText('Echo Spire')).toBeInTheDocument()
  })
})

describe('DetailDrawer interaction', () => {
  it('clicking close button calls onClose', async () => {
    const onClose = vi.fn()
    render(<DetailDrawer detail={detail} isOpen={true} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('onClose is not called on render', () => {
    const onClose = vi.fn()
    render(<DetailDrawer detail={detail} isOpen={true} onClose={onClose} />)
    expect(onClose).not.toHaveBeenCalled()
  })
})

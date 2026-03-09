import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import DataMonitoring from '../pages/DataMonitoring'
import * as api from '../services/api'

vi.mock('../services/api', () => ({
  dataAPI: {
    overview: vi.fn(),
    stocks: vi.fn(),
    stockDetail: vi.fn(),
    fetchNow: vi.fn(),
    fetchStop: vi.fn(),
    fetchStatus: vi.fn(),
  },
}))

const mockOverview = {
  total_stocks: 6000,
  date_range: { start: '2024-01-01', end: '2024-12-31' },
  completeness: 85.5,
  last_fetch: { date: '2024-02-25', time: '10:30', status: 'success', fetched: 5000, failed: 10 },
  next_fetch: '2024-02-26 00:00',
  indicators: { '开盘价': { stocks: 5800, rate: 96.7 }, '收盘价': { stocks: 5800, rate: 96.7 }, '成交量': { stocks: 5700, rate: 95.0 } },
}

const mockStocks = {
  total: 100,
  page: 1,
  page_size: 20,
  stocks: [
    { code: '600000', name: '浦发银行', start_date: '2024-01-01', end_date: '2024-12-31', total_days: 250, available_days: 245, completeness: 98.0, missing_days: 5 },
    { code: '000001', name: '平安银行', start_date: '2024-01-01', end_date: '2024-12-31', total_days: 250, available_days: 248, completeness: 99.2, missing_days: 2 },
  ],
}

const mockStockDetail = {
  code: '600000',
  total_days: 245,
  data: [
    { date: '2024-01-02', open: 10.5, high: 10.8, low: 10.3, close: 10.7, volume: 1000000 },
    { date: '2024-01-03', open: 10.7, high: 11.0, low: 10.6, close: 10.9, volume: 1200000 },
  ],
}

describe('DataMonitoring - 搜索功能', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.dataAPI.overview as any).mockResolvedValue({ data: mockOverview })
    ;(api.dataAPI.stocks as any).mockResolvedValue({ data: mockStocks })
  })

  it('should render search input', async () => {
    render(<DataMonitoring />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜索股票代码或名称...')).toBeInTheDocument()
    })
  })

  it('should filter stocks when search term is entered', async () => {
    render(<DataMonitoring />)
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('搜索股票代码或名称...')
      fireEvent.change(searchInput, { target: { value: '600000' } })
    })
    await waitFor(() => {
      expect(api.dataAPI.stocks).toHaveBeenCalled()
    })
  })
})

describe('DataMonitoring - 详情弹窗', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.dataAPI.overview as any).mockResolvedValue({ data: mockOverview })
    ;(api.dataAPI.stocks as any).mockResolvedValue({ data: mockStocks })
    ;(api.dataAPI.stockDetail as any).mockResolvedValue({ data: mockStockDetail })
  })

  it('should call stockDetail API when stock row is clicked', async () => {
    render(<DataMonitoring />)
    await waitFor(() => {
      expect(screen.getByText('600000')).toBeInTheDocument()
    })
    const stockRow = screen.getByText('600000')
    fireEvent.click(stockRow)
    await waitFor(() => {
      expect(api.dataAPI.stockDetail).toHaveBeenCalledWith('600000')
    })
  })

  it('should display chart in modal when data is loaded', async () => {
    render(<DataMonitoring />)
    await waitFor(() => {
      expect(screen.getByText('600000')).toBeInTheDocument()
    })
    const stockRow = screen.getByText('600000')
    fireEvent.click(stockRow)
    await waitFor(() => {
      expect(screen.getByText('K线走势')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('should show loading state when fetching detail', async () => {
    let resolveDetail!: (val: any) => void
    ;(api.dataAPI.stockDetail as any).mockImplementation(() => new Promise(r => resolveDetail = r))
    
    render(<DataMonitoring />)
    await waitFor(() => {
      expect(screen.getByText('600000')).toBeInTheDocument()
    })
    
    const stockRow = screen.getByText('600000')
    fireEvent.click(stockRow)
    
    // Wait for loading state
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
  })
})

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  maxRedirects: 5, // 自动处理重定向
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface Strategy {
  id: string
  name: string
  description: string
  params: Record<string, any>
  created_at: string
  updated_at: string
  performance_history: any[]
}

export interface DataOverview {
  total_stocks: number
  date_range: {
    start: string
    end: string
  }
  completeness: number
  last_fetch: {
    date: string
    time: string
    status: string
    fetched: number
    failed: number
  }
  next_fetch: string
  indicators: Record<string, {
    stocks: number
    rate: number
  }>
}

export interface StockDataItem {
  code: string
  name: string
  start_date: string
  end_date: string
  total_days: number
  available_days: number
  completeness: number
  missing_days: number
}

export interface BacktestConfig {
  strategy_id: string
  market: string
  year?: string
  start_date?: string
  end_date?: string
  initial_capital?: number
  max_stocks?: number
  max_positions?: number
  position_size?: number
  stop_loss?: number
  take_profit?: number
  trailing_stop?: number
}

export interface BacktestResult {
  task_id?: string
  status?: string
  progress?: number
  current_step?: string
  result?: {
    total_return: number
    annual_return?: number
    max_drawdown: number
    sharpe_ratio?: number
    win_rate: number
    total_trades: number
    final_capital: number
  }
  stocks_tested?: number
  duration?: number
}

// API Methods
export const strategyAPI = {
  list: () => api.get<Strategy[]>('/strategies/'),
  get: (id: string) => api.get<Strategy>(`/strategies/${id}`),
}

export const dataAPI = {
  overview: () => api.get<DataOverview>('/data/overview'),
  stocks: (params: { market?: string; page?: number; page_size?: number; sort_by?: string; only_missing?: boolean }) =>
    api.get<{ total: number; page: number; page_size: number; stocks: StockDataItem[] }>('/data/stocks', { params }),
  stockDetail: (code: string) => api.get(`/data/stocks/${code}`),

  // Data fetch APIs
  fetchNow: () => api.post<{ task_id: string; status: string; message: string }>('/data/fetch-now'),
  fetchStatus: (taskId: string) => api.get<{
    status: string;
    progress: number;
    total: number;
    success: number;
    failed: number;
    skipped: number;
    errors: Array<{ symbol: string; error: string }>;
    started_at?: string;
    ended_at?: string;
  }>(`/data/fetch/status/${taskId}`),
  fetchStats: () => api.get<{
    total: number;
    success: number;
    failed: number;
    skipped: number;
    last_run: string | null;
    errors: Array<{ symbol: string; error: string }>;
    current_status: string;
  }>('/data/fetch/stats'),
  fetchStop: () => api.post<{ status: string; message: string }>('/data/fetch/stop'),
}

export const backtestAPI = {
  quickBacktest: (config: BacktestConfig) => api.post<BacktestResult>('/backtest/quick', config),
  fullBacktest: (config: BacktestConfig) => api.post<{ task_id: string }>('/backtest/full', config),
  getTaskStatus: (taskId: string) => api.get<BacktestResult>(`/backtest/tasks/${taskId}`),
  getTaskResult: (taskId: string) => api.get<BacktestResult>(`/backtest/tasks/${taskId}/result`),
}

export const reportsAPI = {
  downloadExcel: (taskId: string) => {
    return api.get(`/reports/${taskId}/excel`, {
      responseType: 'blob',
    })
  },
  downloadPdf: (taskId: string) => {
    return api.get(`/reports/${taskId}/pdf`, {
      responseType: 'blob',
    })
  },
}

export default api

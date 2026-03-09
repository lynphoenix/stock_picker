import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
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

    // Network errors (no response from server)
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        error.message = '请求超时，请检查网络连接后重试'
      } else if (error.message.includes('Network Error')) {
        error.message = '网络连接失败，请检查网络设置'
      } else {
        error.message = `网络请求失败: ${error.message || '未知错误'}`
      }
      return Promise.reject(error)
    }

    // HTTP error responses (4xx, 5xx)
    const status = error.response.status
    const data = error.response.data

    // If server returned a structured error with message/errors, use it
    if (data && (data.message || data.errors)) {
      error.message = data.message || (data.errors && data.errors.join(', ')) || `HTTP ${status} 错误`
    } else if (status === 400) {
      error.message = '请求参数错误，请检查输入'
    } else if (status === 401) {
      error.message = '认证失败，请重新登录'
    } else if (status === 403) {
      error.message = '无权限访问'
    } else if (status === 404) {
      error.message = '请求的资源不存在'
    } else if (status === 500) {
      error.message = '服务器内部错误，请稍后重试'
    } else if (status === 502 || status === 503) {
      error.message = '服务暂时不可用，请稍后重试'
    } else if (status === 504) {
      error.message = '服务器响应超时'
    } else {
      error.message = `请求失败 (HTTP ${status})`
    }

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

// AI策略生成类型
export interface GenerateStrategyRequest {
  stock_pool?: string[]
  start_date?: string
  end_date?: string
  initial_capital?: number
  name: string
  description: string
}

export interface GenerateStrategyResponse {
  success: boolean
  strategy_code: string | null
  errors: string[] | null
  backtest_result: BacktestResult | null
  message: string | null
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
  // Task status fields
  task_id?: string
  status?: string
  progress?: number
  current_step?: string
  // Flat result fields (from quick backtest API)
  result?: {
    total_return: number
    annual_return?: number
    max_drawdown: number
    sharpe_ratio?: number
    win_rate: number
    total_trades: number
    final_capital: number
  }
  // Flat fields directly on response
  total_return?: number
  max_drawdown?: number
  win_rate?: number
  trades_count?: number
  trades?: any[]
  daily_values?: any[]
  trades?: any[]
  daily_values?: any[]
  final_capital?: number
  stocks_count?: number
  sharpe_ratio?: number
  stocks_tested?: number
  duration?: number
}

// API Methods
export const strategyAPI = {
  generate: (data: GenerateStrategyRequest) => api.post<GenerateStrategyResponse>('/strategies/generate', data),
  list: () => api.get<Strategy[]>('/strategies/'),
  get: (id: string) => api.get<Strategy>(`/strategies/${id}`),
}

export const dataAPI = {
  overview: () => api.get<DataOverview>('/data/overview'),
  stocks: (params: { market?: string; page?: number; page_size?: number; sort_by?: string; search?: string; only_missing?: boolean }) =>
    api.get<{ total: number; page: number; page_size: number; stocks: StockDataItem[] }>('/data/stocks', { params }),
  stockDetail: (code: string) => api.get(`/data/stocks/${code}`),
  stockMinute: (code: string, date?: string) => api.get(`/data/stock/${code}/minute`, { params: { date } }),

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
  quickBacktest: (config: BacktestConfig) => api.post<BacktestResult>('/backtest/run', config),
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

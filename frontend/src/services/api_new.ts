/**
 * API service for strategy generation and backtesting.
 */

export interface GenerateStrategyRequest {
  name: string;
  description: string;
}

export interface BacktestResult {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  trades_count: number;
  holding_periods: number[];
}

export interface GenerateStrategyResponse {
  success: boolean;
  strategy_code: string | null;
  errors: string[] | null;
  backtest_result: BacktestResult | null;
  message: string | null;
}

const API_BASE_URL = '/api/strategies';

export const strategyAPI = {
  /**
   * Generate a trading strategy from natural language description.
   */
  async generate(request: GenerateStrategyRequest): Promise<GenerateStrategyResponse> {
    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },
};

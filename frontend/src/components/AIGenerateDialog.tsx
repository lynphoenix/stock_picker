import { useState } from 'react';
import { strategyAPI, GenerateStrategyResponse } from '../services/api';

interface AIGenerateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: GenerateStrategyResponse) => void;
}

export function AIGenerateDialog({ isOpen, onClose, onSuccess }: AIGenerateDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [stockPool, setStockPool] = useState('000001,600000');
  const [startDate, setStartDate] = useState('20250101');
  const [endDate, setEndDate] = useState('20251231');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<string[] | null>(null);
  const [result, setResult] = useState<GenerateStrategyResponse | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setErrorDetails(null);
    setResult(null);

    try {
      const stockList = stockPool.split(',').map(s => s.trim()).filter(s => s);
      const response = await strategyAPI.generate({
        name,
        description,
        stock_pool: stockList.length > 0 ? stockList : ['000001', '600000'],
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
      });

      setResult(response.data);

      if (response.data.success && onSuccess) {
        onSuccess(response.data);
      }

      if (!response.data.success) {
        // Set main error message
        setError(response.data.message || '策略生成失败');
        // Set detailed errors if available
        if (response.data.errors && response.data.errors.length > 0) {
          setErrorDetails(response.data.errors);
        }
      }
    } catch (err) {
      // Network or HTTP errors
      const errorMessage = err instanceof Error ? err.message : '发生未知错误';
      setError(errorMessage);
      setErrorDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setError(null);
    setErrorDetails(null);
    setResult(null);
    onClose();
  };

  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  const formatNumber = (value: number) => value.toFixed(2);

  return (
    <div className="dialog-overlay" onClick={handleClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 700 }}>
        <h2>AI 创建策略</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="strategy-name">
              策略名称 ({name.length}/100)
            </label>
            <input
              id="strategy-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.slice(0, 100))}
              placeholder="例如：双均线策略"
              required
              disabled={loading}
              maxLength={100}
            />
          </div>

          <div className="form-group">
            <label htmlFor="strategy-description">
              策略描述 ({description.length}/500)
            </label>
            <textarea
              id="strategy-description"
              value={description}
              onChange={(e) => setDescription(e.target.value.slice(0, 500))}
              placeholder="例如：当 MA5 上穿 MA20 时买入，下穿时卖出"
              required
              disabled={loading}
              rows={3}
              maxLength={500}
            />
          </div>

          <div className="form-group">
            <label htmlFor="stock-pool">股票池（逗号分隔）</label>
            <input
              id="stock-pool"
              type="text"
              value={stockPool}
              onChange={(e) => setStockPool(e.target.value)}
              placeholder="例如：000001,600000,300001"
              disabled={loading}
            />
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label htmlFor="start-date">开始日期</label>
              <input
                id="start-date"
                type="text"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                placeholder="YYYYMMDD"
                disabled={loading}
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label htmlFor="end-date">结束日期</label>
              <input
                id="end-date"
                type="text"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                placeholder="YYYYMMDD"
                disabled={loading}
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label htmlFor="initial-capital">初始资金</label>
              <input
                id="initial-capital"
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
                disabled={loading}
              />
            </div>
          </div>

          {error && (
            <div style={{
              color: '#f44336',
              marginBottom: '16px',
              padding: '12px',
              backgroundColor: '#ffebee',
              borderRadius: '4px',
              border: '1px solid #ffcdd2'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: errorDetails ? '8px' : '0' }}>
                {error}
              </div>
              {errorDetails && errorDetails.length > 0 && (
                <ul style={{
                  margin: '0',
                  paddingLeft: '20px',
                  fontSize: '0.9em'
                }}>
                  {errorDetails.map((detail, index) => (
                    <li key={index}>{detail}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button type="button" onClick={handleClose} disabled={loading}>
              取消
            </button>
            <button type="submit" className="btn-primary" disabled={loading || !name || !description}>
              {loading ? '生成中...' : '生成策略'}
            </button>
          </div>
        </form>

        {result?.success && result.backtest_result && (
          <div className="backtest-results">
            <h3>回测结果</h3>
            <div className="metrics">
              <div className="metric">
                <div className="metric-label">总收益率</div>
                <div className={`metric-value ${result.backtest_result.total_return >= 0 ? 'positive' : 'negative'}`}>
                  {formatPercent(result.backtest_result.total_return)}
                </div>
              </div>
              <div className="metric">
                <div className="metric-label">夏普比率</div>
                <div className="metric-value">{formatNumber(result.backtest_result.sharpe_ratio)}</div>
              </div>
              <div className="metric">
                <div className="metric-label">最大回撤</div>
                <div className="metric-value negative">{formatPercent(-result.backtest_result.max_drawdown)}</div>
              </div>
              <div className="metric">
                <div className="metric-label">胜率</div>
                <div className="metric-value">{formatPercent(result.backtest_result.win_rate)}</div>
              </div>
              <div className="metric">
                <div className="metric-label">交易次数</div>
                <div className="metric-value">{result.backtest_result.trades_count}</div>
              </div>
            </div>
          </div>
        )}

        {result?.strategy_code && (
          <div className="code-preview">
            <h3>生成的策略代码</h3>
            <pre>{result.strategy_code}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

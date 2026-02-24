import { useState, useEffect } from 'react'
import { Row, Col, Select, Button, InputNumber, message, Spin, Dropdown } from 'antd'
import { BarChartOutlined, DownloadOutlined, FileExcelOutlined, FilePdfOutlined } from '@ant-design/icons'
import { strategyAPI, backtestAPI, reportsAPI, Strategy, BacktestResult } from '../services/api'
import './StrategyWorkspace.css'

export default function StrategyWorkspace() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [backtesting, setBacktesting] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)

  // Backtest config
  const [config, setConfig] = useState({
    market: 'sh_star',
    year: '2026',
    initial_capital: 1000000,
    max_stocks: 100,
  })

  useEffect(() => {
    loadStrategies()
  }, [])

  const loadStrategies = async () => {
    setLoading(true)
    try {
      const response = await strategyAPI.list()
      setStrategies(response.data)
      if (response.data.length > 0) {
        setSelectedStrategy(response.data[0].id)
      }
    } catch (error) {
      message.error('加载策略列表失败')
    } finally {
      setLoading(false)
    }
  }

  const runQuickBacktest = async () => {
    if (!selectedStrategy) {
      message.warning('请先选择策略')
      return
    }

    setBacktesting(true)
    setResult(null)

    try {
      const response = await backtestAPI.quickBacktest({
        strategy_id: selectedStrategy,
        ...config,
      })

      if (response.data.status === 'success') {
        setResult(response.data)
        message.success(`回测完成！测试了 ${response.data.stocks_tested} 只股票`)
      } else {
        message.error('回测失败')
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '回测请求失败')
    } finally {
      setBacktesting(false)
    }
  }

  // Download handlers
  const handleDownload = async (type: 'excel' | 'pdf') => {
    if (!result?.task_id) {
      message.warning('暂无回测任务ID，无法下载报表')
      return
    }

    try {
      const response = type === 'excel'
        ? await reportsAPI.downloadExcel(result.task_id)
        : await reportsAPI.downloadPdf(result.task_id)

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `backtest_report_${result.task_id}.${type === 'excel' ? 'xlsx' : 'pdf'}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      message.success(`${type === 'excel' ? 'Excel' : 'PDF'} 报表下载成功`)
    } catch (error: any) {
      console.error('Download error:', error)
      message.error(error.response?.data?.detail || '下载失败，请确保后端服务正常运行')
    }
  }

  const downloadMenuItems = {
    items: [
      {
        key: 'excel',
        label: '导出 Excel',
        icon: <FileExcelOutlined />,
        onClick: () => handleDownload('excel'),
      },
      {
        key: 'pdf',
        label: '导出 PDF',
        icon: <FilePdfOutlined />,
        onClick: () => handleDownload('pdf'),
      },
    ],
  }

  return (
    <div className="strategy-workspace" style={{ padding: '40px 24px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 48 }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>回测工作台</h1>
      </div>

      <Row gutter={[40, 40]}>
        {/* Left Panel - Configuration */}
        <Col xs={24} lg={9}>
          <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 32, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
            <Spin spinning={loading}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
                <div>
                  <div style={{ marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>策略</div>
                  <Select
                    value={selectedStrategy}
                    onChange={setSelectedStrategy}
                    style={{ width: '100%' }}
                    size="large"
                    options={strategies.map(s => ({ label: s.name, value: s.id }))}
                  />
                </div>

                <div>
                  <div style={{ marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>市场</div>
                  <Select
                    value={config.market}
                    onChange={(value) => setConfig({ ...config, market: value })}
                    style={{ width: '100%' }}
                    size="large"
                    options={[
                      { label: '科创板', value: 'sh_star' },
                      { label: '全部', value: 'all' },
                      { label: '沪市', value: 'sh_main' },
                      { label: '创业板', value: 'sz_gem' },
                    ]}
                  />
                </div>

                <Row gutter={16}>
                  <Col span={12}>
                    <div style={{ marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>年份</div>
                    <Select
                      value={config.year}
                      onChange={(value) => setConfig({ ...config, year: value })}
                      style={{ width: '100%' }}
                      size="large"
                      options={[
                        { label: '2026', value: '2026' },
                        { label: '2025', value: '2025' },
                        { label: '2024', value: '2024' },
                      ]}
                    />
                  </Col>
                  <Col span={12}>
                    <div style={{ marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>股票数</div>
                    <InputNumber
                      value={config.max_stocks}
                      onChange={(value) => setConfig({ ...config, max_stocks: value || 100 })}
                      style={{ width: '100%' }}
                      size="large"
                      min={10}
                      max={500}
                    />
                  </Col>
                </Row>

                <div>
                  <div style={{ marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>初始资金</div>
                  <InputNumber
                    value={config.initial_capital}
                    onChange={(value) => setConfig({ ...config, initial_capital: value || 1000000 })}
                    style={{ width: '100%' }}
                    size="large"
                    formatter={(value) => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={(value) => value!.replace(/¥\s?|(,*)/g, '') as any}
                    min={100000}
                    max={100000000}
                    step={100000}
                  />
                </div>

                <Button
                  type="primary"
                  size="large"
                  onClick={runQuickBacktest}
                  loading={backtesting}
                  block
                  style={{ marginTop: 12, height: 48, fontSize: 16 }}
                >
                  {backtesting ? '回测中...' : '开始回测'}
                </Button>
              </div>
            </Spin>
          </div>
        </Col>

        {/* Right Panel - Results */}
        <Col xs={24} lg={15}>
          {result ? (
            <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 40, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div style={{ marginBottom: 36, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: 18, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>回测结果</h2>
                {result.task_id && (
                  <Dropdown menu={downloadMenuItems} placement="bottomRight">
                    <Button icon={<DownloadOutlined />} type="text">
                      导出报表
                    </Button>
                  </Dropdown>
                )}
              </div>

              <Row gutter={[24, 32]}>
                <Col xs={24} sm={12}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>总收益率</div>
                    <div style={{
                      fontSize: 42,
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      color: (result.result?.total_return || 0) > 0 ? 'var(--success)' : 'var(--danger)'
                    }}>
                      {result.result?.total_return?.toFixed(2)}%
                    </div>
                  </div>
                </Col>
                <Col xs={24} sm={12}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>最大回撤</div>
                    <div style={{ fontSize: 42, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {Math.abs(result.result?.max_drawdown || 0).toFixed(2)}%
                    </div>
                  </div>
                </Col>
                <Col xs={12}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>胜率</div>
                    <div style={{ fontSize: 28, fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                      {result.result?.win_rate?.toFixed(1)}%
                    </div>
                  </div>
                </Col>
                <Col xs={12}>
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>交易次数</div>
                    <div style={{ fontSize: 28, fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                      {result.result?.total_trades}
                    </div>
                  </div>
                </Col>
              </Row>

              <div style={{ marginTop: 40, paddingTop: 24, borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  测试 {result.stocks_tested} 只股票 · 最终资金 ¥{result.result?.final_capital.toLocaleString()} · 耗时 {result.duration}s
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'rgba(18, 24, 32, 0.4)',
              borderRadius: 12,
              padding: 80,
              border: '1px solid rgba(255, 255, 255, 0.06)',
              textAlign: 'center'
            }}>
              <BarChartOutlined style={{ fontSize: 48, color: 'var(--text-muted)', marginBottom: 16 }} />
              <div style={{ fontSize: 16, color: 'var(--text-secondary)' }}>配置参数后开始回测</div>
            </div>
          )}
        </Col>
      </Row>
    </div>
  )
}

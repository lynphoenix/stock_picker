import { useState, useEffect } from 'react'
import { Row, Col, Table, Tag, Progress, Select, Button, message, Space, DatePicker, Divider } from 'antd'
import { SyncOutlined, PlayCircleOutlined, StopOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { dataAPI, DataOverview, StockDataItem } from '../services/api'
import ReactECharts from 'echarts-for-react'
import './DataMonitoring.css'

const { RangePicker } = DatePicker

interface FetchProgress {
  status: string
  progress: number
  total: number
  success: number
  failed: number
  skipped: number
  errors: Array<{ symbol: string; error: string }>
}

export default function DataMonitoring() {
  const [overview, setOverview] = useState<DataOverview | null>(null)
  const [stocks, setStocks] = useState<StockDataItem[]>([])
  const [_loading, setLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [selectedMarket, setSelectedMarket] = useState('all')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  // Fetch control state
  const [isFetching, setIsFetching] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [fetchProgress, setFetchProgress] = useState<FetchProgress | null>(null)
  const [selectedStockPool, setSelectedStockPool] = useState('all')

  useEffect(() => {
    loadOverview()
  }, [])

  useEffect(() => {
    loadStocks()
  }, [selectedMarket, pagination.current])

  // Fetch polling effect
  useEffect(() => {
    if (taskId && isFetching) {
      const interval = setInterval(async () => {
        try {
          const response = await dataAPI.fetchStatus(taskId)
          setFetchProgress(response.data)

          // Check if completed
          if (response.data.status === 'completed' || response.data.status === 'stopped' || response.data.status === 'failed') {
            setIsFetching(false)
            clearInterval(interval)
            if (response.data.status === 'completed') {
              message.success('数据采集完成')
            }
          }
        } catch (error) {
          console.error('Failed to fetch status:', error)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [taskId, isFetching])

  // Fetch control functions
  const handleFetchNow = async () => {
    try {
      setIsFetching(true)
      const response = await dataAPI.fetchNow()
      setTaskId(response.data.task_id)
      setFetchProgress({
        status: 'started',
        progress: 0,
        total: 0,
        success: 0,
        failed: 0,
        skipped: 0,
        errors: []
      })
      message.info('数据采集已启动')
    } catch (error: any) {
      setIsFetching(false)
      message.error(error.response?.data?.detail || '启动采集失败')
    }
  }

  const handleStopFetch = async () => {
    try {
      await dataAPI.fetchStop()
      setIsFetching(false)
      message.info('采集已停止')
    } catch (error) {
      message.error('停止采集失败')
    }
  }

  const handleDateRangeChange = (dates: any, dateStrings: string[]) => {
    // Store the date range for future use (passed to API when triggering fetch)
    // Currently just validates the input
    if (!dates || !dateStrings || dateStrings.length !== 2) {
      console.log('Date range cleared')
    } else {
      console.log('Date range selected:', dateStrings[0].replace(/-/g, ''), '-', dateStrings[1].replace(/-/g, ''))
    }
  }

  const loadOverview = async () => {
    setLoading(true)
    try {
      const response = await dataAPI.overview()
      setOverview(response.data)
    } catch (error) {
      message.error('加载数据总览失败')
    } finally {
      setLoading(false)
    }
  }

  const loadStocks = async () => {
    setTableLoading(true)
    try {
      const response = await dataAPI.stocks({
        market: selectedMarket,
        page: pagination.current,
        page_size: pagination.pageSize,
      })
      setStocks(response.data.stocks)
      setPagination({
        ...pagination,
        total: response.data.total,
      })
    } catch (error) {
      message.error('加载股票列表失败')
    } finally {
      setTableLoading(false)
    }
  }

  const indicatorOptions = overview ? {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(18, 24, 32, 0.95)',
      borderColor: '#1e2936',
      textStyle: { color: '#e6edf3' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%',
        color: '#8b949e'
      },
      splitLine: {
        lineStyle: { color: '#1e2936' }
      }
    },
    yAxis: {
      type: 'category',
      data: Object.keys(overview.indicators),
      axisLabel: { color: '#e6edf3' }
    },
    series: [{
      type: 'bar',
      data: Object.values(overview.indicators).map(v => v.rate),
      itemStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: '#00d9ff' },
            { offset: 1, color: '#0099cc' }
          ]
        }
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{c}%',
        color: '#e6edf3'
      }
    }]
  } : {}

  const columns = [
    {
      title: '股票代码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
      render: (code: string) => <span className="font-mono">{code}</span>
    },
    {
      title: '数据范围',
      key: 'range',
      render: (_: any, record: StockDataItem) => (
        <span className="font-mono text-sm">
          {record.start_date} ~ {record.end_date}
        </span>
      )
    },
    {
      title: '数据天数',
      dataIndex: 'available_days',
      key: 'available_days',
      width: 100,
      render: (days: number) => <span className="font-mono">{days}</span>
    },
    {
      title: '完整率',
      dataIndex: 'completeness',
      key: 'completeness',
      width: 180,
      render: (completeness: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress
            percent={completeness}
            size="small"
            strokeColor={{
              '0%': completeness > 95 ? '#2ea043' : completeness > 80 ? '#d29922' : '#f85149',
              '100%': completeness > 95 ? '#4ac46e' : completeness > 80 ? '#f0b94c' : '#ff6b6b'
            }}
            format={() => `${completeness.toFixed(1)}%`}
          />
        </div>
      )
    },
    {
      title: '缺失天数',
      dataIndex: 'missing_days',
      key: 'missing_days',
      width: 100,
      render: (missing: number) => (
        <Tag color={missing === 0 ? 'success' : missing < 10 ? 'warning' : 'error'} className="font-mono">
          {missing}
        </Tag>
      )
    }
  ]

  return (
    <div style={{ padding: '40px 24px', maxWidth: 1600, margin: '0 auto' }}>
      <div style={{ marginBottom: 48, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>数据监控</h1>
        <Button type="primary" icon={<SyncOutlined />} onClick={() => { loadOverview(); loadStocks() }}>
          刷新
        </Button>
      </div>

      {/* Fetch Control Panel */}
      <div style={{
        background: 'rgba(18, 24, 32, 0.6)',
        borderRadius: 12,
        padding: 24,
        border: '1px solid rgba(255, 255, 255, 0.06)',
        marginBottom: 32
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>
            数据采集控制
          </h3>
          <Space>
            {!isFetching ? (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleFetchNow}
                size="large"
              >
                立即采集
              </Button>
            ) : (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleStopFetch}
                size="large"
              >
                停止
              </Button>
            )}
          </Space>
        </div>

        {/* Stock pool and date range */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <div>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>股票池:</span>
            <Select
              value={selectedStockPool}
              onChange={setSelectedStockPool}
              style={{ width: 140 }}
              disabled={isFetching}
              options={[
                { label: '全部', value: 'all' },
                { label: 'AI软件', value: 'AI软件' },
                { label: '半导体', value: '半导体' },
                { label: '机器人', value: '机器人' },
              ]}
            />
          </div>
          <div>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>日期范围:</span>
            <RangePicker
              onChange={handleDateRangeChange}
              disabled={isFetching}
              format="YYYY-MM-DD"
              allowClear
            />
          </div>
        </div>

        {/* Progress bar */}
        {isFetching && fetchProgress && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                采集进度 {fetchProgress.total > 0 ? `(${fetchProgress.success + fetchProgress.failed + fetchProgress.skipped}/${fetchProgress.total})` : ''}
              </span>
              <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {fetchProgress.progress}%
              </span>
            </div>
            <Progress
              percent={fetchProgress.progress}
              status={fetchProgress.status === 'failed' ? 'exception' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068'
              }}
            />
          </div>
        )}

        {/* Statistics cards */}
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>总计</div>
              <div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                {fetchProgress?.total || 0}
              </div>
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>成功</div>
              <div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--success)' }}>
                {fetchProgress?.success || 0}
              </div>
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>失败</div>
              <div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--error)' }}>
                {fetchProgress?.failed || 0}
              </div>
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>跳过</div>
              <div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--warning)' }}>
                {fetchProgress?.skipped || 0}
              </div>
            </div>
          </Col>
        </Row>

        {/* Error logs */}
        {fetchProgress && fetchProgress.errors && fetchProgress.errors.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <Divider style={{ margin: '16px 0' }} />
            <h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 12, color: 'var(--error)' }}>
              <CloseCircleOutlined style={{ marginRight: 8 }} />
              错误日志
            </h4>
            <div style={{ maxHeight: 150, overflow: 'auto' }}>
              {fetchProgress.errors.map((error, index) => (
                <div key={index} style={{
                  padding: '8px 12px',
                  background: 'rgba(255, 77, 79, 0.1)',
                  borderRadius: 4,
                  marginBottom: 8,
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)'
                }}>
                  <span style={{ color: 'var(--error)', fontWeight: 500 }}>{error.symbol}</span>
                  <span style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>{error.error}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Overview Cards */}
      {overview && (
        <>
          <Row gutter={[20, 20]} style={{ marginBottom: 48 }}>
            <Col xs={12} lg={6}>
              <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>股票总数</div>
                <div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>
                  {overview.total_stocks.toLocaleString()}
                </div>
              </div>
            </Col>
            <Col xs={12} lg={6}>
              <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>完整率</div>
                <div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--success)' }}>
                  {overview.completeness.toFixed(1)}%
                </div>
              </div>
            </Col>
            <Col xs={12} lg={6}>
              <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>上次采集</div>
                <div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {overview.last_fetch.fetched}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                  {overview.last_fetch.date} {overview.last_fetch.time}
                </div>
              </div>
            </Col>
            <Col xs={12} lg={6}>
              <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>失败数</div>
                <div style={{
                  fontSize: 36,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: overview.last_fetch.failed > 0 ? 'var(--warning)' : 'var(--text-secondary)'
                }}>
                  {overview.last_fetch.failed}
                </div>
              </div>
            </Col>
          </Row>

          {/* Indicator Chart */}
          <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 32, border: '1px solid rgba(255, 255, 255, 0.06)', marginBottom: 48 }}>
            <h3 style={{ fontSize: 16, fontWeight: 500, marginBottom: 24, color: 'var(--text-primary)' }}>指标完整性</h3>
            <ReactECharts option={indicatorOptions} style={{ height: 240 }} />
          </div>
        </>
      )}

      {/* Stock List Table */}
      <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 32, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>股票列表</h3>
          <Select
            value={selectedMarket}
            onChange={setSelectedMarket}
            style={{ width: 140 }}
            options={[
              { label: '全部', value: 'all' },
              { label: '科创板', value: 'sh_star' },
              { label: '沪市', value: 'sh_main' },
              { label: '创业板', value: 'sz_gem' },
            ]}
          />
        </div>

        <Table
          dataSource={stocks}
          columns={columns}
          loading={tableLoading}
          rowKey="code"
          pagination={{
            ...pagination,
            onChange: (page) => setPagination({ ...pagination, current: page }),
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 只`,
          }}
        />
      </div>
    </div>
  )
}

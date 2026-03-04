import { useState, useEffect } from 'react'
import { Row, Col, Table, Tag, Progress, Select, Button, message, Space, DatePicker, Divider, Input, Modal, Tabs } from 'antd'
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

interface StockDetail {
  code: string
  name: string
  total_days: number
  data: Array<{
    date: string
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
}

interface MinuteData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function DataMonitoring() {
  const [overview, setOverview] = useState<DataOverview | null>(null)
  const [stocks, setStocks] = useState<StockDataItem[]>([])
  const [_loading, setLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [selectedMarket, setSelectedMarket] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('code')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  // Detail modal state
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedStock, setSelectedStock] = useState<StockDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [chartPeriod, setChartPeriod] = useState<'minute' | 'day' | 'week' | 'month'>('day')
  const [minuteData, setMinuteData] = useState<MinuteData[]>([])
  

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
  }, [selectedMarket, pagination.current, sortBy])

  // Fetch polling effect
  useEffect(() => {
    if (taskId && isFetching) {
      const interval = setInterval(async () => {
        try {
          const response = await dataAPI.fetchStatus(taskId)
          setFetchProgress(response.data)
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

  const handleFetchNow = async () => {
    try {
      setIsFetching(true)
      const response = await dataAPI.fetchNow()
      setTaskId(response.data.task_id)
      setFetchProgress({ status: 'started', progress: 0, total: 0, success: 0, failed: 0, skipped: 0, errors: [] })
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
        sort_by: sortBy,
        market: selectedMarket,
        search: searchTerm,
        page: pagination.current,
        page_size: pagination.pageSize,
      })
      setStocks(response.data.stocks)
      setPagination({ ...pagination, total: response.data.total })
    } catch (error) {
      message.error('加载股票列表失败')
    } finally {
      setTableLoading(false)
    }
  }

  const handleStockClick = async (record: StockDataItem) => {
    setDetailModalVisible(true)
    setDetailLoading(true)
    setChartPeriod('day')  // Default to day chart
    setMinuteData([])
    setSelectedStock(null)  // Clear previous stock
    try {
      const [detailRes, minuteRes] = await Promise.all([
        dataAPI.stockDetail(record.code),
        dataAPI.stockMinute(record.code)
      ])
      setSelectedStock(detailRes.data)
      if (minuteRes.data && minuteRes.data.data) {
        setMinuteData(minuteRes.data.data)
      }
    } catch (error) {
      message.error('加载股票详情失败')
      setDetailModalVisible(false)
    } finally {
      setDetailLoading(false)
    }
  }

  // Get minute chart options (分时图)
  const getMinuteChartOptions = () => {
    if (!minuteData || minuteData.length === 0) return {}

    const times = minuteData.map(d => d.time)
    const prices = minuteData.map(d => d.close)
    const volumes = minuteData.map(d => d.volume)
    const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length

    // 分时图Y轴：使用前一日收盘价作为基准（同花顺逻辑）
    // 需要从日线数据中获取前一日收盘价
    console.log("DEBUG minuteData:", minuteData.length, minuteData[0]); const prevClose = minuteData.length > 0 ? minuteData[0].open : selectedStock?.data?.[selectedStock.data.length - 2]?.close
    console.log("DEBUG prevClose:", prevClose, "selectedStock:", selectedStock?.data?.length)
    const allPrices = minuteData.flatMap(d => [d.high, d.low])
    const minPrice = Math.min(...allPrices)
    const maxPrice = Math.max(...allPrices)

    const offset = prevClose ? Math.max(Math.abs(maxPrice - prevClose), Math.abs(minPrice - prevClose)) : (maxPrice - minPrice) * 0.1
    const yMin = prevClose ? prevClose - offset : minPrice * 0.95
    const yMax = prevClose ? prevClose + offset : maxPrice * 1.05
    console.log("DEBUG yMin:", yMin, "yMax:", yMax, "minPrice:", minPrice, "maxPrice:", maxPrice)

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'line' }, backgroundColor: 'rgba(18, 24, 32, 0.95)', borderColor: '#1e2936', textStyle: { color: '#e6edf3' } },
      grid: { left: '3%', right: '3%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', rotate: 45 }, axisLine: { lineStyle: { color: '#1e2936' } } },
      yAxis: [
        { type: 'value', name: '价格', min: Math.floor(yMin), max: Math.ceil(yMax), axisLabel: { color: '#8b949e' }, axisLine: { lineStyle: { color: '#1e2936' } }, splitLine: { lineStyle: { color: '#1e2936' } } },
        { type: 'value', name: '成交量', axisLabel: { color: '#8b949e', formatter: (val: number) => (val / 10000).toFixed(0) + '万' }, axisLine: { show: false }, splitLine: { show: false } }
      ],
      dataZoom: [{ type: 'inside', start: 0, end: 100 }],
      series: [
        { name: '价格', type: 'line', data: prices, smooth: true, lineStyle: { color: '#00d9ff', width: 2 }, markLine: { silent: true, lineStyle: { color: '#666', type: 'dashed' }, data: [{ yAxis: prevClose || avgPrice }], label: { formatter: '昨收: {c}' } }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0, 217, 255, 0.2)' }, { offset: 1, color: 'rgba(0, 217, 255, 0.02)' }] } } },
        { name: '成交量', type: 'bar', yAxisIndex: 1, data: volumes, itemStyle: { color: 'rgba(0, 217, 255, 0.3)' } }
      ]
    }
  }

  // Aggregate data for weekly/monthly K-line
  const aggregateData = (data: StockDetail['data'], period: 'day' | 'week' | 'month') => {
    if (!data || data.length === 0) return []

    // Sort by date
    const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date))

    if (period === 'day') {
      // Show last 60 days by default
      return sorted.slice(-60)
    }

    // Group by week or month
    const groups: { [key: string]: typeof data } = {}
    for (const d of sorted) {
      const date = new Date(d.date)
      let key: string
      if (period === 'week') {
        // Get Monday of the week
        const day = date.getDay()
        const monday = new Date(date)
        monday.setDate(date.getDate() - (day === 0 ? 6 : day - 1))
        key = monday.toISOString().split('T')[0]
      } else {
        // Month key: YYYY-MM-01
        key = d.date.substring(0, 7) + '-01'
      }
      if (!groups[key]) groups[key] = []
      groups[key].push(d)
    }

    // Aggregate each group to OHLC
    const result: typeof data = []
    for (const [key, items] of Object.entries(groups)) {
      if (items.length === 0) continue
      const opens = items[0].open
      const closes = items[items.length - 1].close
      const highs = Math.max(...items.map(i => i.high))
      const lows = Math.min(...items.map(i => i.low))
      const volumes = items.reduce((sum, i) => sum + i.volume, 0)
      result.push({
        date: key,
        open: opens,
        high: highs,
        low: lows,
        close: closes,
        volume: volumes
      })
    }
    return result
  }

  const getChartOptions = () => {
    // Show minute chart if selected
    if (chartPeriod === 'minute') {
      return getMinuteChartOptions()
    }

    if (!selectedStock || !selectedStock.data || selectedStock.data.length === 0) return {}

    // Get filtered/aggregated data based on period
    const displayData = chartPeriod === 'day'
      ? selectedStock.data.slice(-60)  // Last 60 days
      : aggregateData(selectedStock.data, chartPeriod)

    const dates = displayData.map(d => d.date)
    const candleData = displayData.map(d => [d.open, d.close, d.low, d.high])
    const volumes = displayData.map(d => d.volume)

    // K线Y轴：用当前显示窗口第一天的收盘价作为基准
    const prevClose = displayData[0]?.close
    const allPrices = displayData.flatMap(d => [d.high, d.low])
    const minPrice = Math.min(...allPrices)
    const maxPrice = Math.max(...allPrices)

    const offset = prevClose ? Math.max(Math.abs(maxPrice - prevClose), Math.abs(minPrice - prevClose)) : (maxPrice - minPrice) * 0.1
    const yMin = prevClose ? prevClose - offset : minPrice * 0.95
    const yMax = prevClose ? prevClose + offset : maxPrice * 1.05
    console.log("DEBUG yMin:", yMin, "yMax:", yMax, "minPrice:", minPrice, "maxPrice:", maxPrice)

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(18, 24, 32, 0.95)', borderColor: '#1e2936', textStyle: { color: '#e6edf3' } },
      grid: { left: '3%', right: '3%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#8b949e', rotate: 45 }, axisLine: { lineStyle: { color: '#1e2936' } } },
      yAxis: [
        { type: 'value', name: '价格', min: Math.floor(yMin), max: Math.ceil(yMax), axisLabel: { color: '#8b949e' }, axisLine: { lineStyle: { color: '#1e2936' } }, splitLine: { lineStyle: { color: '#1e2936' } } },
        { type: 'value', name: '成交量', axisLabel: { color: '#8b949e', formatter: (val: number) => (val / 10000).toFixed(0) + '万' }, axisLine: { show: false }, splitLine: { show: false } }
      ],
      dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100 }],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: candleData,
          itemStyle: {
            color: '#ef4444',
            color0: '#22c55e',
            borderColor: '#ef4444',
            borderColor0: '#22c55e'
          }
        },
        { name: '成交量', type: 'bar', yAxisIndex: 1, data: volumes, itemStyle: { color: 'rgba(0, 217, 255, 0.3)' } }
      ]
    }
  }

  const indicatorOptions = overview ? {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: 'rgba(18, 24, 32, 0.95)', borderColor: '#1e2936', textStyle: { color: '#e6edf3' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: '#8b949e' }, splitLine: { lineStyle: { color: '#1e2936' } } },
    yAxis: { type: 'category', data: Object.keys(overview.indicators), axisLabel: { color: '#e6edf3' } },
    series: [{ type: 'bar', data: Object.values(overview.indicators).map(v => v.rate), itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#00d9ff' }, { offset: 1, color: '#0099cc' }] } }, label: { show: true, position: 'right', formatter: '{c}%', color: '#e6edf3' } }]
  } : {}

  const columns = [
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 120, render: (code: string) => <span className="font-mono">{code}</span> },
    { title: '股票名称', dataIndex: 'name', key: 'name', width: 120 },
    { title: '数据范围', key: 'range', render: (_: any, record: StockDataItem) => <span className="font-mono text-sm">{record.start_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')} ~ {record.end_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}</span> },
    { title: '数据天数', dataIndex: 'available_days', key: 'available_days', width: 100, render: (days: number) => <span className="font-mono">{days}</span> },
    { title: '完整率', dataIndex: 'completeness', key: 'completeness', width: 180, render: (completeness: number) => <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Progress percent={completeness} size="small" strokeColor={{ '0%': completeness > 95 ? '#2ea043' : completeness > 80 ? '#d29922' : '#f85149', '100%': completeness > 95 ? '#4ac46e' : completeness > 80 ? '#f0b94c' : '#ff6b6b' }} format={() => `${completeness.toFixed(1)}%`} /></div> },
    { title: '缺失天数', dataIndex: 'missing_days', key: 'missing_days', width: 100, render: (missing: number) => <Tag color={missing === 0 ? 'success' : missing < 10 ? 'warning' : 'error'} className="font-mono">{missing}</Tag> }
  ]

  return (
    <div style={{ padding: '40px 24px', maxWidth: 1600, margin: '0 auto' }}>
      <div style={{ marginBottom: 48, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>数据监控</h1>
        <Button type="primary" icon={<SyncOutlined />} onClick={() => { loadOverview(); loadStocks() }}>刷新</Button>
      </div>
      <div style={{ background: 'rgba(18, 24, 32, 0.6)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)', marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>数据采集控制</h3>
          <Space>{!isFetching ? <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleFetchNow} size="large">立即采集</Button> : <Button danger icon={<StopOutlined />} onClick={handleStopFetch} size="large">停止</Button>}</Space>
        </div>
        <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <div><span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>股票池:</span><Select value={selectedStockPool} onChange={setSelectedStockPool} style={{ width: 140 }} disabled={isFetching} options={[{ label: '全部', value: 'all' }, { label: 'AI软件', value: 'AI软件' }, { label: '半导体', value: '半导体' }, { label: '机器人', value: '机器人' }]} /></div>
          <div><span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>日期范围:</span><RangePicker onChange={handleDateRangeChange} disabled={isFetching} format="YYYY-MM-DD" allowClear /></div>
        </div>
        {isFetching && fetchProgress && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}><span style={{ color: 'var(--text-secondary)' }}>采集进度 {fetchProgress.total > 0 ? `(${fetchProgress.success + fetchProgress.failed + fetchProgress.skipped}/${fetchProgress.total})` : ''}</span><span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{fetchProgress.progress}%</span></div>
            <Progress percent={fetchProgress.progress} status={fetchProgress.status === 'failed' ? 'exception' : 'active'} strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} />
          </div>
        )}
        <Row gutter={[16, 16]}><Col xs={12} sm={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}><div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>总计</div><div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>{fetchProgress?.total || 0}</div></div></Col><Col xs={12} sm={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}><div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>成功</div><div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--success)' }}>{fetchProgress?.success || 0}</div></div></Col><Col xs={12} sm={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}><div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>失败</div><div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--error)' }}>{fetchProgress?.failed || 0}</div></div></Col><Col xs={12} sm={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16, textAlign: 'center' }}><div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>跳过</div><div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--warning)' }}>{fetchProgress?.skipped || 0}</div></div></Col></Row>
        {fetchProgress && fetchProgress.errors && fetchProgress.errors.length > 0 && (<div style={{ marginTop: 20 }}><Divider style={{ margin: '16px 0' }} /><h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 12, color: 'var(--error)' }}><CloseCircleOutlined style={{ marginRight: 8 }} />错误日志</h4><div style={{ maxHeight: 150, overflow: 'auto' }}>{fetchProgress.errors.map((error, index) => <div key={index} style={{ padding: '8px 12px', background: 'rgba(255, 77, 79, 0.1)', borderRadius: 4, marginBottom: 8, fontSize: 12, fontFamily: 'var(--font-mono)' }}><span style={{ color: 'var(--error)', fontWeight: 500 }}>{error.symbol}</span><span style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>{error.error}</span></div>)}</div></div>)}
      </div>
      {overview && (<><Row gutter={[20, 20]} style={{ marginBottom: 48 }}><Col xs={12} lg={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}><div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>股票总数</div><div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>{overview.total_stocks.toLocaleString()}</div></div></Col><Col xs={12} lg={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}><div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>完整率</div><div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--success)' }}>{overview.completeness.toFixed(1)}%</div></div></Col><Col xs={12} lg={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}><div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>上次采集</div><div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{overview.last_fetch.fetched}</div><div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>{overview.last_fetch.date} {overview.last_fetch.time}</div></div></Col><Col xs={12} lg={6}><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 24, border: '1px solid rgba(255, 255, 255, 0.06)' }}><div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>失败数</div><div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 600, color: overview.last_fetch.failed > 0 ? 'var(--warning)' : 'var(--text-secondary)' }}>{overview.last_fetch.failed}</div></div></Col></Row><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 32, border: '1px solid rgba(255, 255, 255, 0.06)', marginBottom: 48 }}><h3 style={{ fontSize: 16, fontWeight: 500, marginBottom: 24, color: 'var(--text-primary)' }}>指标完整性</h3><ReactECharts option={indicatorOptions} style={{ height: 240 }} /></div></>)}
      <div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 12, padding: 32, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>股票列表</h3>
          <Space wrap><Input
            id="searchInput"
            placeholder="搜索代码或名称"
            onChange={(e) => setSearchTerm(e.target.value)}
            onPressEnter={() => {
              console.log('Searching for:', searchTerm)
              loadStocks()
            }}
            style={{ width: 200 }}
          />
          <Button onClick={() => loadStocks()}>搜索</Button><Select value={selectedMarket} onChange={(value) => { setSelectedMarket(value); setPagination({ ...pagination, current: 1 }) }} style={{ width: 140 }} options={[{ label: '全部', value: 'all' }, { label: '科创板', value: 'sh_star' }, { label: '沪市', value: 'sh_main' }, { label: '创业板', value: 'sz_gem' }]} />
          <Select value={sortBy} onChange={(value) => { setSortBy(value); setPagination({ ...pagination, current: 1 }) }} style={{ width: 120 }} options={[{ label: '代码', value: 'code' }, { label: '名称', value: 'name' }, { label: '完整率', value: 'completeness' }]} /></Space>
        </div>
        <Table dataSource={stocks} columns={columns} loading={tableLoading} rowKey="code" onRow={(record) => ({ onClick: () => handleStockClick(record), style: { cursor: 'pointer' } })} pagination={{ ...pagination, onChange: (page) => setPagination({ ...pagination, current: page }), showSizeChanger: false, showTotal: (total) => `共 ${total} 只` }} />
      </div>
      <Modal title={selectedStock ? `股票详情 - ${selectedStock.code} ${selectedStock.name || ""}` : '股票详情'} open={detailModalVisible} onCancel={() => setDetailModalVisible(false)} footer={[<Button key="close" onClick={() => setDetailModalVisible(false)}>关闭</Button>]} width={900} centered>
        {detailLoading ? <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div> : selectedStock ? <div><div style={{ marginBottom: 16 }}><span style={{ color: 'var(--text-secondary)' }}>数据天数: </span><span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{selectedStock.total_days} 天</span></div><div style={{ background: 'rgba(18, 24, 32, 0.4)', borderRadius: 8, padding: 16 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h4 style={{ fontSize: 14, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>{chartPeriod === 'minute' ? '分时走势' : chartPeriod === 'day' ? '日K走势' : chartPeriod === 'week' ? '周K走势' : '月K走势'}</h4>
          <Tabs
            activeKey={chartPeriod}
            onChange={(key) => setChartPeriod(key as 'minute' | 'day' | 'week' | 'month')}
            size="small"
            items={[
              { key: 'minute', label: '分时' },
              { key: 'day', label: '日K' },
              { key: 'week', label: '周K' },
              { key: 'month', label: '月K' }
            ]}
          />
        </div>
        <ReactECharts option={getChartOptions()} style={{ height: 350 }} /></div></div> : <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>暂无数据</div>}
      </Modal>
    </div>
  )
}

import { Outlet, Link, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu } from 'antd'
import { RocketOutlined, DatabaseOutlined, ApiOutlined } from '@ant-design/icons'
import './Layout.css'

const { Header, Content } = AntLayout

export default function Layout() {
  const location = useLocation()

  return (
    <AntLayout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <ApiOutlined className="logo-icon" />
            <div className="logo-text">
              <h1 className="font-display">Quant Terminal</h1>
              <span className="logo-subtitle">量化回测终端</span>
            </div>
          </div>

          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            className="main-menu"
            items={[
              {
                key: '/strategy',
                icon: <RocketOutlined />,
                label: <Link to="/strategy">策略回测</Link>,
              },
              {
                key: '/data',
                icon: <DatabaseOutlined />,
                label: <Link to="/data">数据监控</Link>,
              },
            ]}
          />

          <div className="header-status">
            <div className="status-indicator">
              <span className="status-dot status-pulse"></span>
              <span className="font-mono">API Connected</span>
            </div>
          </div>
        </div>
      </Header>

      <Content className="app-content">
        <div className="content-wrapper">
          <Outlet />
        </div>
      </Content>
    </AntLayout>
  )
}

import React, { useState } from 'react'
import { Layout, Menu, Avatar, Dropdown, theme } from 'antd'
import {
  DashboardOutlined,
  TeamOutlined,
  CalendarOutlined,
  BarChartOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import './MainLayout.css'

const { Header, Content, Sider } = Layout

const MainLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Дашборд',
    },
    {
      key: '/clients',
      icon: <TeamOutlined />,
      label: 'Клиенты',
    },
    {
      key: '/events',
      icon: <CalendarOutlined />,
      label: 'События',
    },
    {
      key: '/statistics',
      icon: <BarChartOutlined />,
      label: 'Статистика',
    },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Профиль',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Настройки',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
    },
  ]

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  const handleUserMenuClick = ({ key }) => {
    if (key === 'logout') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      navigate('/login')
    }
  }

  const user = JSON.parse(localStorage.getItem('user') || '{}')

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={240}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div className="logo">
          <span className="logo-icon">🤗</span>
          {!collapsed && <span>CRM Уют</span>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          }}
        >
          <Dropdown
            menu={{
              items: userMenuItems,
              onClick: handleUserMenuClick,
            }}
            placement="bottomRight"
          >
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>{user.first_name || 'Администратор'}</span>
              <Avatar icon={<UserOutlined />} />
            </div>
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: 8,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout

import React, { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Spin, Empty } from 'antd'
import {
  TeamOutlined,
  UserOutlined,
  StarOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { clientsApi, eventsApi } from '../../api/client'
import dayjs from 'dayjs'
import './Dashboard.css'

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    total: 0,
    vip: 0,
    active: 0,
    regular: 0,
    lead: 0,
  })
  const [recentClients, setRecentClients] = useState([])
  const [upcomingEvents, setUpcomingEvents] = useState([])

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [clientsRes, eventsRes] = await Promise.all([
        clientsApi.list(),
        eventsApi.list(),
      ])

      const clients = clientsRes.data.results || clientsRes.data || []
      const events = eventsRes.data.results || eventsRes.data || []

      // Статистика
      const statsData = {
        total: clients.length,
        vip: clients.filter(c => c.status === 'vip').length,
        active: clients.filter(c => c.status === 'active').length,
        regular: clients.filter(c => c.status === 'regular').length,
        lead: clients.filter(c => c.status === 'lead').length,
      }
      setStats(statsData)

      // Последние 5 клиентов
      const sortedClients = [...clients].sort((a, b) => 
        new Date(b.created_at) - new Date(a.created_at)
      ).slice(0, 5)
      setRecentClients(sortedClients)

      // Ближайшие события
      const now = dayjs()
      const upcoming = events
        .filter(e => !e.is_completed && dayjs(e.event_date).isAfter(now))
        .sort((a, b) => new Date(a.event_date) - new Date(b.event_date))
        .slice(0, 5)
      setUpcomingEvents(upcoming)

    } catch (error) {
      console.error('Ошибка загрузки данных:', error)
    } finally {
      setLoading(false)
    }
  }

  const statusMap = {
    vip: { color: 'gold', text: 'VIP' },
    active: { color: 'green', text: 'Активный' },
    regular: { color: 'blue', text: 'Постоянный' },
    lead: { color: 'orange', text: 'Лид' },
    inactive: { color: 'red', text: 'Неактивный' },
  }

  const columns = [
    {
      title: 'Клиент',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (_, record) => `${record.first_name} ${record.last_name}`,
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={statusMap[status]?.color || 'default'}>
          {statusMap[status]?.text || status}
        </Tag>
      ),
    },
    {
      title: 'Дата добавления',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('DD.MM.YYYY'),
    },
  ]

  const eventColumns = [
    {
      title: 'Событие',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: 'Клиент',
      dataIndex: ['client', 'first_name'],
      key: 'client',
      render: (_, record) => `${record.client?.first_name} ${record.client?.last_name}`,
    },
    {
      title: 'Дата',
      dataIndex: 'event_date',
      key: 'event_date',
      render: (date) => dayjs(date).format('DD.MM.YYYY HH:mm'),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="dashboard">
      <h1 style={{ marginBottom: 24 }}>📊 Дашборд</h1>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Всего клиентов"
              value={stats.total}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="VIP клиенты"
              value={stats.vip}
              prefix={<StarOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Активные"
              value={stats.active}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Лиды"
              value={stats.lead}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="🆕 Новые клиенты" extra={<a href="/clients">Все клиенты</a>}>
            {recentClients.length > 0 ? (
              <Table
                columns={columns}
                dataSource={recentClients}
                rowKey="id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="Нет клиентов" />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="📅 Ближайшие события" extra={<a href="/events">Все события</a>}>
            {upcomingEvents.length > 0 ? (
              <Table
                columns={eventColumns}
                dataSource={upcomingEvents}
                rowKey="id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="Нет событий" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard

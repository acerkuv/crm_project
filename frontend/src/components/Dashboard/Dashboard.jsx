import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Spin, Button, Space, Timeline, Progress } from 'antd';
import {
  UserOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  StarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ReloadOutlined,
  CalendarFilled,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './Dashboard.css';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

const Dashboard = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalClients: 0,
    activeClients: 0,
    vipClients: 0,
    todayEvents: 0,
    upcomingEvents: 0,
    completedEvents: 0,
    totalEvents: 0,
  });
  const [recentClients, setRecentClients] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [statusDistribution, setStatusDistribution] = useState([]);
  const [eventsByType, setEventsByType] = useState([]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Получаем всех клиентов
      const clientsRes = await api.get('/api/clients/');
      const clients = clientsRes.data.results || clientsRes.data || [];
      
      // Получаем все события
      const eventsRes = await api.get('/api/scheduled-events/');
      const events = eventsRes.data.results || eventsRes.data || [];

      // Статистика
      const today = dayjs().startOf('day');
      const tomorrow = today.add(1, 'day');

      const todayEvents = events.filter(e => dayjs(e.scheduled_date).isSame(today, 'day'));
      const upcomingEvents = events.filter(e => 
        dayjs(e.scheduled_date).isAfter(today) && !e.is_completed
      );
      const completedEvents = events.filter(e => e.is_completed);

      setStats({
        totalClients: clients.length,
        activeClients: clients.filter(c => c.status === 'active').length,
        vipClients: clients.filter(c => c.status === 'vip').length,
        todayEvents: todayEvents.length,
        upcomingEvents: upcomingEvents.length,
        completedEvents: completedEvents.length,
        totalEvents: events.length,
      });

      // Статус клиентов
      const statusCount = {};
      clients.forEach(c => {
        statusCount[c.status] = (statusCount[c.status] || 0) + 1;
      });
      const statusColors = {
        vip: '#fadb14',
        active: '#52c41a',
        regular: '#1890ff',
        lead: '#fa8c16',
        inactive: '#d9d9d9',
      };
      const statusNames = {
        vip: 'VIP',
        active: 'Активные',
        regular: 'Постоянные',
        lead: 'Лиды',
        inactive: 'Неактивные',
      };
      setStatusDistribution(
        Object.entries(statusCount).map(([key, value]) => ({
          name: statusNames[key] || key,
          value,
          color: statusColors[key] || '#1890ff',
        }))
      );

      // Типы событий
      const typeCount = {};
      events.forEach(e => {
        typeCount[e.event_type] = (typeCount[e.event_type] || 0) + 1;
      });
      const typeNames = {
        call: 'Звонки',
        meeting: 'Встречи',
        birthday: 'Поздравления',
        reminder: 'Напоминания',
        custom: 'Свои',
      };
      const typeColors = {
        call: '#1890ff',
        meeting: '#722ed1',
        birthday: '#eb2f96',
        reminder: '#fa8c16',
        custom: '#13c2c2',
      };
      setEventsByType(
        Object.entries(typeCount).map(([key, value]) => ({
          name: typeNames[key] || key,
          value,
          color: typeColors[key] || '#1890ff',
        }))
      );

      // Последние клиенты
      setRecentClients(clients.slice(0, 5));

      // Последние события
      setRecentEvents(events.slice(0, 5));

    } catch (error) {
      console.error('Ошибка загрузки дашборда:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Цвета для круговой диаграммы
  const COLORS = ['#fadb14', '#52c41a', '#1890ff', '#fa8c16', '#d9d9d9'];

  const clientColumns = [
    {
      title: 'Имя',
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
      render: (status) => {
        const map = {
          vip: <Tag color="gold">⭐ VIP</Tag>,
          active: <Tag color="green">✅ Активный</Tag>,
          regular: <Tag color="blue">🔄 Постоянный</Tag>,
          lead: <Tag color="orange">🆕 Лид</Tag>,
          inactive: <Tag color="red">⏸️ Неактивный</Tag>,
        };
        return map[status] || <Tag>{status}</Tag>;
      },
    },
  ];

  const eventColumns = [
    {
      title: 'Событие',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: 'Клиент',
      dataIndex: 'client_full_name',
      key: 'client_full_name',
      render: (name) => name || '—',
    },
    {
      title: 'Дата',
      dataIndex: 'scheduled_date',
      key: 'scheduled_date',
      render: (date) => dayjs(date).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Статус',
      dataIndex: 'is_completed',
      key: 'is_completed',
      render: (completed) => (
        <Tag color={completed ? 'green' : 'blue'}>
          {completed ? '✅ Выполнено' : '⏳ Ожидает'}
        </Tag>
      ),
    },
  ];

  return (
    <div className="dashboard" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>📊 Дашборд</h1>
        <Button icon={<ReloadOutlined />} onClick={fetchDashboardData} loading={loading}>
          Обновить
        </Button>
      </div>

      <Spin spinning={loading}>
        {/* Статистика */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="👥 Всего клиентов"
                value={stats.totalClients}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="✅ Активные"
                value={stats.activeClients}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="⭐ VIP"
                value={stats.vipClients}
                prefix={<StarOutlined />}
                valueStyle={{ color: '#fadb14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="📅 Сегодня"
                value={stats.todayEvents}
                prefix={<CalendarOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="⏳ Предстоит"
                value={stats.upcomingEvents}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={4}>
            <Card>
              <Statistic
                title="✅ Выполнено"
                value={stats.completedEvents}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Графики */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Card title="Статусы клиентов">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Типы событий">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={eventsByType}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#1890ff" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        {/* Последние записи */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Card title="🆕 Последние клиенты">
              <Table
                columns={clientColumns}
                dataSource={recentClients}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="📅 Последние события">
              <Table
                columns={eventColumns}
                dataSource={recentEvents}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default Dashboard;

import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Spin, Button, Space, Select, DatePicker } from 'antd';
import {
  UserOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  StarOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  ReloadOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, AreaChart, ComposedChart
} from 'recharts';
import './Statistics.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

const Statistics = () => {
  const [loading, setLoading] = useState(false);
  const [clients, setClients] = useState([]);
  const [events, setEvents] = useState([]);
  const [period, setPeriod] = useState('month');
  const [dateRange, setDateRange] = useState([dayjs().startOf('month'), dayjs()]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [clientsRes, eventsRes] = await Promise.all([
        api.get('/api/clients/'),
        api.get('/api/scheduled-events/'),
      ]);
      setClients(clientsRes.data.results || clientsRes.data || []);
      setEvents(eventsRes.data.results || eventsRes.data || []);
    } catch (error) {
      console.error('Ошибка загрузки данных:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Статистика по клиентам
  const getClientStats = () => {
    const total = clients.length;
    const byStatus = {};
    const byMonth = {};
    const byDay = {};

    clients.forEach(c => {
      byStatus[c.status] = (byStatus[c.status] || 0) + 1;
      const month = dayjs(c.created_at).format('MM.YYYY');
      byMonth[month] = (byMonth[month] || 0) + 1;
      const day = dayjs(c.created_at).format('DD.MM');
      byDay[day] = (byDay[day] || 0) + 1;
    });

    return { total, byStatus, byMonth, byDay };
  };

  // Статистика по событиям
  const getEventStats = () => {
    const total = events.length;
    const byType = {};
    const byStatus = { completed: 0, pending: 0 };
    const byMonth = {};
    const byDay = {};

    events.forEach(e => {
      byType[e.event_type] = (byType[e.event_type] || 0) + 1;
      if (e.is_completed) byStatus.completed++;
      else byStatus.pending++;

      const month = dayjs(e.scheduled_date).format('MM.YYYY');
      byMonth[month] = (byMonth[month] || 0) + 1;
      const day = dayjs(e.scheduled_date).format('DD.MM');
      byDay[day] = (byDay[day] || 0) + 1;
    });

    return { total, byType, byStatus, byMonth, byDay };
  };

  const clientStats = getClientStats();
  const eventStats = getEventStats();

  const statusColors = {
    vip: '#fadb14',
    active: '#52c41a',
    regular: '#1890ff',
    lead: '#fa8c16',
    inactive: '#d9d9d9',
  };

  const statusNames = {
    vip: '⭐ VIP',
    active: '✅ Активные',
    regular: '🔄 Постоянные',
    lead: '🆕 Лиды',
    inactive: '⏸️ Неактивные',
  };

  const typeColors = {
    call: '#1890ff',
    meeting: '#722ed1',
    birthday: '#eb2f96',
    reminder: '#fa8c16',
    custom: '#13c2c2',
  };

  const typeNames = {
    call: '📞 Звонки',
    meeting: '📅 Встречи',
    birthday: '🎂 Поздравления',
    reminder: '🔔 Напоминания',
    custom: '📝 Свои',
  };

  const statusData = Object.entries(clientStats.byStatus).map(([key, value]) => ({
    name: statusNames[key] || key,
    value,
    color: statusColors[key] || '#1890ff',
  }));

  const typeData = Object.entries(eventStats.byType).map(([key, value]) => ({
    name: typeNames[key] || key,
    value,
    color: typeColors[key] || '#1890ff',
  }));

  const eventStatusData = [
    { name: '✅ Выполнено', value: eventStats.byStatus.completed, color: '#52c41a' },
    { name: '⏳ Ожидает', value: eventStats.byStatus.pending, color: '#fa8c16' },
  ];

  const clientTimeline = Object.entries(clientStats.byMonth).map(([key, value]) => ({
    month: key,
    clients: value,
  })).slice(-6);

  const eventTimeline = Object.entries(eventStats.byMonth).map(([key, value]) => ({
    month: key,
    events: value,
  })).slice(-6);

  // Топ клиенты по активности
  const topClients = clients
    .map(c => ({
      ...c,
      eventCount: events.filter(e => e.client === c.id).length,
    }))
    .sort((a, b) => b.eventCount - a.eventCount)
    .slice(0, 5);

  const topColumns = [
    {
      title: 'Клиент',
      key: 'name',
      render: (_, record) => `${record.first_name} ${record.last_name}`,
    },
    {
      title: 'Событий',
      dataIndex: 'eventCount',
      key: 'eventCount',
      sorter: (a, b) => a.eventCount - b.eventCount,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const map = {
          vip: <Tag color="gold">VIP</Tag>,
          active: <Tag color="green">Активный</Tag>,
          regular: <Tag color="blue">Постоянный</Tag>,
          lead: <Tag color="orange">Лид</Tag>,
          inactive: <Tag color="red">Неактивный</Tag>,
        };
        return map[status] || <Tag>{status}</Tag>;
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>📊 Статистика</h1>
        <Space>
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 120 }}
          >
            <Select.Option value="week">Неделя</Select.Option>
            <Select.Option value="month">Месяц</Select.Option>
            <Select.Option value="quarter">Квартал</Select.Option>
            <Select.Option value="year">Год</Select.Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            Обновить
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {/* Общая статистика */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="👥 Всего клиентов"
                value={clientStats.total}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="📅 Всего событий"
                value={eventStats.total}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="✅ Выполнено событий"
                value={eventStats.byStatus.completed}
                suffix={`/ ${eventStats.total}`}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="⏳ В работе"
                value={eventStats.byStatus.pending}
                suffix={`/ ${eventStats.total}`}
                valueStyle={{ color: '#fa8c16' }}
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
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
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
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Card title="Динамика клиентов">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={clientTimeline}>
                  <defs>
                    <linearGradient id="colorClients" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1890ff" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#1890ff" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" />
                  <YAxis />
                  <CartesianGrid strokeDasharray="3 3" />
                  <Tooltip />
                  <Area type="monotone" dataKey="clients" stroke="#1890ff" fillOpacity={1} fill="url(#colorClients)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Динамика событий">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={eventTimeline}>
                  <defs>
                    <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#722ed1" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#722ed1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" />
                  <YAxis />
                  <CartesianGrid strokeDasharray="3 3" />
                  <Tooltip />
                  <Area type="monotone" dataKey="events" stroke="#722ed1" fillOpacity={1} fill="url(#colorEvents)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        {/* Топ клиенты */}
        <Row style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="🏆 Самые активные клиенты">
              <Table
                columns={topColumns}
                dataSource={topClients}
                rowKey="id"
                pagination={false}
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default Statistics;

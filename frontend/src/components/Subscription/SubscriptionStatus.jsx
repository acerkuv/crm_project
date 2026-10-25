import React, { useState, useEffect } from 'react';
import { Card, Progress, Tag, Button, Space, Typography, Alert, Statistic, Row, Col, Spin } from 'antd';
import { CrownOutlined, ThunderboltOutlined, UserOutlined, CalendarOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

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

const SubscriptionStatus = () => {
  const [loading, setLoading] = useState(false);
  const [subscription, setSubscription] = useState(null);
  const navigate = useNavigate();

  const fetchSubscription = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/users/subscription/');
      setSubscription(response.data);
    } catch (error) {
      console.error('Ошибка загрузки подписки:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscription();
  }, []);

  if (loading) return <Spin />;
  if (!subscription) return null;

  const { subscription: sub, limits } = subscription;
  
  const planColors = {
    free: 'default',
    basic: 'blue',
    pro: 'gold',
    enterprise: 'purple',
  };

  const planLabels = {
    free: 'Бесплатный',
    basic: 'Базовый',
    pro: 'Про',
    enterprise: 'Корпоративный',
  };

  return (
    <Card 
      title={
        <Space>
          <CrownOutlined style={{ color: sub.is_active ? '#fadb14' : '#d9d9d9' }} />
          <span>Мой тариф</span>
          <Tag color={sub.is_active ? planColors[sub.plan] : 'default'}>
            {planLabels[sub.plan] || sub.plan}
          </Tag>
          {!sub.is_active && <Tag color="red">Истекла</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Button 
            type="primary" 
            onClick={() => navigate('/plans')}
          >
            Сменить тариф
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchSubscription} size="small">
            Обновить
          </Button>
        </Space>
      }
      style={{ marginBottom: 24 }}
    >
      {sub.is_active && sub.expires_at && (
        <Alert
          message={`Подписка активна до ${new Date(sub.expires_at).toLocaleDateString('ru-RU')}`}
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      
      {!sub.is_active && (
        <Alert
          message="Подписка истекла"
          description="Обновите тариф для продолжения работы"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic
              title="Клиенты"
              value={limits.clients.used}
              suffix={` / ${limits.clients.max || '∞'}`}
              prefix={<UserOutlined />}
            />
            {limits.clients.max && (
              <Progress 
                percent={Math.round(limits.clients.percent)} 
                size="small"
                status={limits.clients.percent > 90 ? 'exception' : 'active'}
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic
              title="События в этом месяце"
              value={limits.events.used}
              suffix={` / ${limits.events.max || '∞'}`}
              prefix={<CalendarOutlined />}
            />
            {limits.events.max && (
              <Progress 
                percent={Math.round(limits.events.percent)} 
                size="small"
                status={limits.events.percent > 90 ? 'exception' : 'active'}
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card size="small">
            <Statistic
              title="AI запросы"
              value={limits.ai.used}
              suffix={` / ${limits.ai.max || '∞'}`}
              prefix={<ThunderboltOutlined />}
            />
            {limits.ai.max && (
              <Progress 
                percent={Math.round(limits.ai.percent)} 
                size="small"
                status={limits.ai.percent > 90 ? 'exception' : 'active'}
              />
            )}
          </Card>
        </Col>
      </Row>
    </Card>
  );
};

export default SubscriptionStatus;

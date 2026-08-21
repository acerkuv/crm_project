import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Tag, Space, Typography, Spin, message, Modal, Alert } from 'antd';
import { 
  CheckOutlined, 
  CloseOutlined, 
  CrownOutlined, 
  ThunderboltOutlined,
  UserOutlined,
  CalendarOutlined,
  RocketOutlined,
  StarOutlined,
  TeamOutlined
} from '@ant-design/icons';
import axios from 'axios';
import SubscriptionStatus from './SubscriptionStatus';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const { Title, Text, Paragraph } = Typography;

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

const Plans = () => {
  const [loading, setLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const plans = [
    {
      id: 'free',
      name: 'Бесплатный',
      icon: <UserOutlined />,
      price: '0 ₽',
      period: 'всегда',
      description: 'Для знакомства с системой',
      features: [
        { name: 'Клиентов', value: '10', included: true },
        { name: 'Событий в месяц', value: '50', included: true },
        { name: 'AI запросов в месяц', value: '0', included: false },
        { name: 'Поддержка', value: 'Базовая', included: true },
        { name: 'Экспорт данных', value: 'Нет', included: false },
        { name: 'API доступ', value: 'Нет', included: false },
        { name: 'Team доступ', value: 'Нет', included: false },
      ],
      color: '#8c8c8c',
      popular: false,
    },
    {
      id: 'basic',
      name: 'Базовый',
      icon: <RocketOutlined />,
      price: '500 ₽',
      period: 'в месяц',
      description: 'Для небольших бизнесов',
      features: [
        { name: 'Клиентов', value: '50', included: true },
        { name: 'Событий в месяц', value: '200', included: true },
        { name: 'AI запросов в месяц', value: '10', included: true },
        { name: 'Поддержка', value: 'Приоритетная', included: true },
        { name: 'Экспорт данных', value: 'CSV', included: true },
        { name: 'API доступ', value: 'Да', included: true },
        { name: 'Team доступ', value: 'Нет', included: false },
      ],
      color: '#1890ff',
      popular: false,
    },
    {
      id: 'pro',
      name: 'Про',
      icon: <StarOutlined />,
      price: '1 500 ₽',
      period: 'в месяц',
      description: 'Для растущего бизнеса',
      features: [
        { name: 'Клиентов', value: '200', included: true },
        { name: 'Событий в месяц', value: '500', included: true },
        { name: 'AI запросов в месяц', value: '100', included: true },
        { name: 'Поддержка', value: 'VIP 24/7', included: true },
        { name: 'Экспорт данных', value: 'CSV, Excel, PDF', included: true },
        { name: 'API доступ', value: 'Полный', included: true },
        { name: 'Team доступ', value: 'До 5', included: true },
      ],
      color: '#faad14',
      popular: true,
    },
    {
      id: 'enterprise',
      name: 'Корпоративный',
      icon: <TeamOutlined />,
      price: '5 000 ₽',
      period: 'в месяц',
      description: 'Для крупных компаний',
      features: [
        { name: 'Клиентов', value: '∞', included: true },
        { name: 'Событий в месяц', value: '∞', included: true },
        { name: 'AI запросов в месяц', value: '1000', included: true },
        { name: 'Поддержка', value: 'Персональный менеджер', included: true },
        { name: 'Экспорт данных', value: 'Все форматы', included: true },
        { name: 'API доступ', value: 'Полный', included: true },
        { name: 'Team доступ', value: '∞', included: true },
      ],
      color: '#722ed1',
      popular: false,
    },
  ];

  const fetchCurrentPlan = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/users/subscription/');
      setCurrentPlan(response.data.subscription.plan);
    } catch (error) {
      console.error('Ошибка загрузки плана:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentPlan();
  }, []);

  const handleUpgrade = (plan) => {
    setSelectedPlan(plan);
    setShowUpgradeModal(true);
  };

  const handleConfirmUpgrade = async () => {
    message.info(`🔜 Оплата через платёжную систему будет доступна скоро!`);
    setShowUpgradeModal(false);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <Title level={1}>
          <ThunderboltOutlined style={{ color: '#faad14', marginRight: 12 }} />
          Выберите тариф
        </Title>
        <Text type="secondary" style={{ fontSize: 18 }}>
          Выберите подходящий тариф для вашего бизнеса
        </Text>
      </div>

      <SubscriptionStatus />

      <Row gutter={[24, 24]}>
        {plans.map((plan) => {
          const isCurrent = plan.id === currentPlan;
          const isPopular = plan.popular;

          return (
            <Col xs={24} md={12} lg={6} key={plan.id}>
              <Card
                style={{
                  height: '100%',
                  borderColor: isPopular ? plan.color : undefined,
                  borderWidth: isPopular ? 2 : 1,
                  position: 'relative',
                }}
                title={
                  <Space>
                    <span style={{ color: plan.color, fontSize: 24 }}>{plan.icon}</span>
                    <span style={{ fontSize: 20, fontWeight: 600 }}>{plan.name}</span>
                  </Space>
                }
                extra={
                  isPopular && (
                    <Tag color="gold" style={{ fontSize: 12 }}>
                      ★ Популярный
                    </Tag>
                  )
                }
              >
                <div style={{ textAlign: 'center', marginBottom: 16 }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: plan.color }}>
                    {plan.price}
                  </div>
                  <div style={{ fontSize: 14, color: '#999' }}>{plan.period}</div>
                </div>

                <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 24 }}>
                  {plan.description}
                </Paragraph>

                <div style={{ marginBottom: 24 }}>
                  {plan.features.map((feature, index) => (
                    <div
                      key={index}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '6px 0',
                        borderBottom: index < plan.features.length - 1 ? '1px solid #f0f0f0' : 'none',
                      }}
                    >
                      {feature.included ? (
                        <CheckOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      ) : (
                        <CloseOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                      )}
                      <span style={{ flex: 1 }}>{feature.name}</span>
                      <span style={{ fontWeight: 500 }}>{feature.value}</span>
                    </div>
                  ))}
                </div>

                <Button
                  type={isCurrent ? 'default' : isPopular ? 'primary' : 'default'}
                  block
                  size="large"
                  style={{
                    backgroundColor: isCurrent ? undefined : isPopular ? plan.color : undefined,
                    borderColor: isCurrent ? undefined : isPopular ? plan.color : undefined,
                    color: isCurrent ? undefined : isPopular ? '#fff' : undefined,
                  }}
                  onClick={() => {
                    if (isCurrent) {
                      message.info('Это ваш текущий тариф');
                    } else {
                      handleUpgrade(plan);
                    }
                  }}
                >
                  {isCurrent ? (
                    '✅ Текущий тариф'
                  ) : (
                    'Выбрать тариф'
                  )}
                </Button>
              </Card>
            </Col>
          );
        })}
      </Row>

      <Modal
        title="Подтверждение смены тарифа"
        open={showUpgradeModal}
        onCancel={() => setShowUpgradeModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setShowUpgradeModal(false)}>
            Отмена
          </Button>,
          <Button key="confirm" type="primary" onClick={handleConfirmUpgrade}>
            Подтвердить
          </Button>,
        ]}
      >
        {selectedPlan && (
          <div>
            <Alert
              message="Выберите способ оплаты"
              description={
                <div>
                  <p style={{ marginTop: 12 }}>
                    Вы переходите на тариф <strong>{selectedPlan.name}</strong>
                  </p>
                  <p>
                    Стоимость: <strong>{selectedPlan.price}</strong> {selectedPlan.period}
                  </p>
                  <p style={{ color: '#999', fontSize: 12 }}>
                    💳 Оплата будет доступна после настройки платёжной системы
                  </p>
                </div>
              }
              type="info"
              showIcon
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Plans;

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Space, Divider, Spin, Progress, Alert, Tag } from 'antd';
import { 
  UserOutlined, 
  PhoneOutlined, 
  MailOutlined, 
  MessageOutlined,
  CrownOutlined,
  RocketOutlined,
  TeamOutlined,
  CalendarOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Profile.css';

const Profile = () => {
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    fetchProfile();
  }, []);

   const fetchProfile = async () => {
    try {
      setLoading(true);
      const [profileRes, subRes] = await Promise.all([
        api.get('/users/profile/'),
        api.get('/users/subscription/'),
      ]);
      setProfile(profileRes.data);
      setSubscription(subRes.data);
      form.setFieldsValue({
        email: profileRes.data.user.email || '',
        first_name: profileRes.data.telegram.first_name || '',
        last_name: profileRes.data.telegram.last_name || '',
        phone: profileRes.data.telegram.phone || '',
        username: profileRes.data.telegram.username || '',
      });
    } catch (error) {
      console.error('Ошибка загрузки профиля:', error);
      message.error(error.response?.data?.error || 'Не удалось загрузить профиль');
    } finally {
      setLoading(false);
    }
  };

  const onFinish = async (values) => {
    try {
      setLoading(true);
      await api.patch('/users/profile/', values);
      message.success('Профиль успешно обновлен!');
      await fetchProfile();
    } catch (error) {
      console.error('Ошибка обновления профиля:', error);
      message.error(error.response?.data?.error || 'Не удалось обновить профиль');
    } finally {
      setLoading(false);
    }
  };

  if (!profile) {
    return (
      <div className="profile-loading">
        <Spin size="large" tip="Загрузка профиля..." />
      </div>
    );
  }

  const getRoleName = (role) => {
    const roles = {
      'owner': 'Владелец',
      'admin': 'Администратор',
      'manager': 'Менеджер',
      'viewer': 'Наблюдатель',
    };
    return roles[role] || role;
  };

  return (
    <div className="profile-container">
      <Card title="Мой профиль" className="profile-card">
        <div className="profile-content">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* Telegram информация */}
            <div className="profile-section telegram-section">
              <h3>
                <MessageOutlined /> Информация из Telegram
              </h3>
              <div className="profile-info-grid">
                <div className="info-item">
                  <span className="info-label">Telegram ID:</span>
                  <span className="info-value">{profile.telegram.telegram_id}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Username:</span>
                  <span className="info-value">@{profile.telegram.username || 'не указан'}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Роль:</span>
                  <span className="info-value">{getRoleName(profile.telegram.role)}</span>
                </div>
              </div>
            </div>

            <Divider />

            {/* Информация о подписке */}
            <div className="profile-section subscription-section">
              <h3>
                <CrownOutlined /> Подписка
              </h3>
                          {/* Лимиты и использование */}
            {subscription && (
              <>
                <div className="profile-section limits-section">
                  <h3>
                    <RocketOutlined /> Лимиты и использование
                  </h3>

                  {/* Предупреждение если лимит превышен */}
                  {subscription.limits?.clients?.max && subscription.limits.clients.used > subscription.limits.clients.max && (
                    <Alert
                      type="warning"
                      showIcon
                      message="Лимит клиентов превышен"
                      description={`У вас ${subscription.limits.clients.used} клиентов, а лимит плана — ${subscription.limits.clients.max}. Обновите тариф, чтобы добавлять новых.`}
                      style={{ marginBottom: 16 }}
                    />
                  )}

                  {/* Клиенты */}
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>
                        <TeamOutlined /> Клиенты
                      </span>
                      <span>
                        <strong>{subscription.limits?.clients?.used ?? 0}</strong>
                        {' / '}
                        {subscription.limits?.clients?.max ?? '∞'}
                      </span>
                    </div>
                    <Progress
                      percent={Math.min(100, Math.round(subscription.limits?.clients?.percent ?? 0))}
                      status={
                        subscription.limits?.clients?.max && subscription.limits.clients.used >= subscription.limits.clients.max
                          ? 'exception'
                          : 'active'
                      }
                      showInfo={false}
                    />
                  </div>

                  {/* События */}
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>
                        <CalendarOutlined /> События в этом месяце
                      </span>
                      <span>
                        <strong>{subscription.limits?.events?.used ?? 0}</strong>
                        {' / '}
                        {subscription.limits?.events?.max ?? '∞'}
                      </span>
                    </div>
                    <Progress
                      percent={Math.min(100, Math.round(subscription.limits?.events?.percent ?? 0))}
                      status={
                        subscription.limits?.events?.max && subscription.limits.events.used >= subscription.limits.events.max
                          ? 'exception'
                          : 'active'
                      }
                      showInfo={false}
                    />
                  </div>

                  {/* AI запросы */}
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>
                        <RobotOutlined /> AI запросы в этом месяце
                      </span>
                      <span>
                        <strong>{subscription.limits?.ai?.used ?? 0}</strong>
                        {' / '}
                        {subscription.limits?.ai?.max || '—'}
                      </span>
                    </div>
                    <Progress
                      percent={Math.min(100, Math.round(subscription.limits?.ai?.percent ?? 0))}
                      showInfo={false}
                    />
                  </div>

                  <Button
                    type="primary"
                    icon={<RocketOutlined />}
                    onClick={() => navigate('/plans')}
                    block
                    size="large"
                    style={{ marginTop: 8 }}
                  >
                    Обновить тариф
                  </Button>
                </div>

                <Divider />
              </>
            )}
              <div className="profile-info-grid">
                <div className="info-item">
                  <span className="info-label">План:</span>
                  <span className="info-value subscription-plan">
                    {profile.subscription.plan}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-label">Статус:</span>
                  <span className={`info-value subscription-status ${profile.subscription.is_active ? 'active' : 'inactive'}`}>
                    {profile.subscription.is_active ? '✅ Активна' : '❌ Неактивна'}
                  </span>
                </div>
                {profile.subscription.expires_at && (
                  <div className="info-item">
                    <span className="info-label">Действует до:</span>
                    <span className="info-value">
                      {new Date(profile.subscription.expires_at).toLocaleDateString('ru-RU', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <Divider />

            {/* Форма редактирования */}
            <div className="profile-section edit-section">
              <h3>Редактировать профиль</h3>
              <Form
                form={form}
                layout="vertical"
                onFinish={onFinish}
                className="profile-form"
              >
                <Form.Item
                  name="first_name"
                  label="Имя"
                  rules={[{ required: true, message: 'Введите имя' }]}
                >
                  <Input prefix={<UserOutlined />} placeholder="Имя" />
                </Form.Item>

                <Form.Item
                  name="last_name"
                  label="Фамилия"
                >
                  <Input prefix={<UserOutlined />} placeholder="Фамилия" />
                </Form.Item>

                <Form.Item
                  name="phone"
                  label="Телефон"
                  rules={[
                    { pattern: /^\+?[0-9]{10,15}$/, message: 'Введите корректный номер телефона' }
                  ]}
                >
                  <Input prefix={<PhoneOutlined />} placeholder="+79001234567" />
                </Form.Item>

                <Form.Item
                  name="email"
                  label="Email"
                  rules={[
                    { type: 'email', message: 'Введите корректный email' }
                  ]}
                >
                  <Input prefix={<MailOutlined />} placeholder="email@example.com" />
                </Form.Item>

                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} size="large">
                    Сохранить изменения
                  </Button>
                </Form.Item>
              </Form>
            </div>
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default Profile;

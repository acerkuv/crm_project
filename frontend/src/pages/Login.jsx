import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Alert, Steps, Space, Typography } from 'antd';
import { SendOutlined, UserOutlined, LockOutlined, CheckCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const { Text } = Typography;

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [form] = Form.useForm();
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstall, setShowInstall] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Проверяем, что приложение уже установлено
    if (window.matchMedia('(display-mode: standalone)').matches) {
      console.log('📱 Приложение уже установлено');
      setShowInstall(false);
      return;
    }

    // Слушаем событие установки
    const handler = (e) => {
      console.log('✅ beforeinstallprompt сработал!');
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstall(true);
    };

    window.addEventListener('beforeinstallprompt', handler);
    
    // Слушаем событие успешной установки
    window.addEventListener('appinstalled', () => {
      console.log('✅ Приложение установлено!');
      setShowInstall(false);
      message.success('✅ Приложение успешно установлено!');
    });

    console.log('🔍 Слушатель beforeinstallprompt добавлен');

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, []);

  const handleInstall = async () => {
    console.log('🔍 handleInstall вызван');
    
    if (!deferredPrompt) {
      message.info(
        'Для установки нажмите на три точки (⋮) в правом верхнем углу и выберите "Установить приложение CRM Уют..."',
        5
      );
      return;
    }
    
    try {
      deferredPrompt.prompt();
      const result = await deferredPrompt.userChoice;
      
      if (result.outcome === 'accepted') {
        message.success('✅ Приложение установлено!');
        setShowInstall(false);
      } else {
        message.info('Установка отменена');
      }
      setDeferredPrompt(null);
    } catch (error) {
      console.error('Ошибка установки:', error);
      message.error('Ошибка при установке');
    }
  };

  // Шаг 1: Ввод кода (упрощенно, без Telegram ID)
  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/users/verify-code/`, {
        code: values.code,
      });
      
      const { token, user } = response.data;
      
      // Сохраняем токен и данные пользователя
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      
      message.success(`Добро пожаловать, ${user.first_name || 'Пользователь'}!`);
      navigate('/');
      
    } catch (error) {
      console.error('Ошибка входа:', error);
      if (error.response?.status === 400) {
        message.error(error.response?.data?.error || 'Неверный или просроченный код');
      } else {
        message.error(error.response?.data?.error || 'Ошибка входа');
      }
    } finally {
      setLoading(false);
    }
  };

  console.log('🔍 Рендер Login, showInstall:', showInstall);

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: '#f0f2f5'
    }}>
      <Card style={{ width: 450, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <SendOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <h1 style={{ marginTop: 8 }}>CRM Уют</h1>
          <p style={{ color: '#999' }}>Безопасный вход через Telegram</p>
          
          {/* Кнопка установки приложения */}
          <Button 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={handleInstall}
            style={{ marginBottom: 8 }}
            block
            size="large"
          >
            📱 Установить приложение
          </Button>
          
          <Text type="secondary" style={{ fontSize: 12 }}>
            {showInstall 
              ? '✅ Нажмите для установки' 
              : 'Или через меню: ⋮ → Установить приложение'}
          </Text>
        </div>

        <Alert
          message="Как получить код?"
          description={
            <div>
              <p>1. Откройте Telegram бота</p>
              <p>2. Отправьте команду <code>/login</code></p>
              <p>3. Введите полученный код ниже</p>
            </div>
          }
          type="info"
          style={{ marginBottom: 16 }}
        />

        <Form onFinish={onFinish} layout="vertical">
          <Form.Item
            name="code"
            label="Код из Telegram"
            rules={[
              { required: true, message: 'Введите код' },
              { len: 6, message: 'Код должен содержать 6 цифр' }
            ]}
          >
            <Input
              prefix={<LockOutlined />}
              placeholder="123456"
              size="large"
              maxLength={6}
              style={{ letterSpacing: 8, fontSize: 20, fontWeight: 'bold' }}
              autoFocus
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loading}
              icon={<CheckCircleOutlined />}
            >
              Войти
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;

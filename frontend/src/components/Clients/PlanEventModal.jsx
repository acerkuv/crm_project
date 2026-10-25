import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, DatePicker, Button, Space, message, Row, Col } from 'antd';
import { CalendarOutlined, UserOutlined, ClockCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import locale from 'antd/es/date-picker/locale/ru_RU';

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

const PlanEventModal = ({ visible, client, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);

  // Загружаем существующие события клиента
  useEffect(() => {
    if (client && visible) {
      fetchClientEvents();
    }
  }, [client, visible]);

  const fetchClientEvents = async () => {
    try {
      const response = await api.get(`/api/scheduled-events/?client=${client.id}`);
      const data = response.data.results || response.data || [];
      setEvents(data);
    } catch (error) {
      console.error('Ошибка загрузки событий:', error);
    }
  };

  const handleSubmit = async (values) => {
    if (!client) {
      message.error('Клиент не выбран');
      return;
    }

    setLoading(true);
    try {
      // Объединяем дату и время
      const scheduledDate = values.scheduled_date
        .hour(values.scheduled_time.hour())
        .minute(values.scheduled_time.minute())
        .second(0);

      const payload = {
        client: client.id,
        title: values.title,
        description: values.description || '',
        event_type: values.event_type,
        scheduled_date: scheduledDate.toISOString(),
      };

      await api.post('/api/scheduled-events/', payload);
      message.success('✅ Событие создано!');
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error) {
      console.error('❌ Ошибка создания события:', error);
      message.error('Ошибка при создании события');
    } finally {
      setLoading(false);
    }
  };

  const eventTypes = {
    call: { label: '📞 Звонок', color: 'blue' },
    meeting: { label: '📅 Встреча', color: 'purple' },
    birthday: { label: '🎂 Поздравление', color: 'pink' },
    reminder: { label: '🔔 Напоминание', color: 'orange' },
    custom: { label: '📝 Своё', color: 'default' },
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CalendarOutlined style={{ color: '#1890ff' }} />
          <span>Планирование события</span>
          {client && (
            <span style={{ fontSize: '14px', color: '#666', marginLeft: 8 }}>
              для <strong>{client.first_name} {client.last_name}</strong>
            </span>
          )}
        </div>
      }
      open={visible}
      onCancel={() => {
        form.resetFields();
        onClose();
      }}
      footer={null}
      width={600}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          scheduled_date: dayjs(),
          scheduled_time: dayjs().hour(9).minute(0),
          event_type: 'reminder',
        }}
      >
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name="title"
              label="Заголовок"
              rules={[{ required: true, message: 'Введите заголовок события' }]}
            >
              <Input placeholder="Например: Позвонить клиенту" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name="description"
              label="Описание"
            >
              <Input.TextArea rows={3} placeholder="Дополнительная информация (опционально)" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="event_type"
              label="Тип события"
              rules={[{ required: true, message: 'Выберите тип' }]}
            >
              <Select placeholder="Выберите тип события">
                {Object.entries(eventTypes).map(([key, value]) => (
                  <Select.Option key={key} value={key}>
                    {value.label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="scheduled_date"
              label="Дата"
              rules={[{ required: true, message: 'Выберите дату' }]}
            >
              <DatePicker
                format="DD.MM.YYYY"
                placeholder="Выберите дату"
                style={{ width: '100%' }}
                locale={locale}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name="scheduled_time"
              label="Время"
              rules={[{ required: true, message: 'Выберите время' }]}
            >
              <DatePicker.TimePicker
                format="HH:mm"
                placeholder="Выберите время"
                style={{ width: '100%' }}
                minuteStep={15}
                hourStep={1}
              />
            </Form.Item>
          </Col>
        </Row>

        {client && (
          <div style={{ 
            padding: '12px', 
            background: '#f5f5f5', 
            borderRadius: '8px', 
            marginBottom: '16px' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <UserOutlined />
              <span>Клиент: <strong>{client.first_name} {client.last_name}</strong></span>
              {client.phone && (
                <span style={{ color: '#666', marginLeft: 8 }}>📞 {client.phone}</span>
              )}
            </div>
          </div>
        )}

        <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>
              Отмена
            </Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              Создать событие
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default PlanEventModal;

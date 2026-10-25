import React, { useState, useEffect } from 'react';
import { 
  Table, Card, Button, Space, Tag, message, Spin, Select, 
  Modal, Form, Input, DatePicker, Row, Col, Tabs, Badge,
  Timeline, Calendar as AntCalendar, Alert, Popconfirm, Tooltip,
  Divider, Grid
} from 'antd';
import { 
  ReloadOutlined, CheckCircleOutlined, PlusOutlined,
  CalendarOutlined, ClockCircleOutlined, UserOutlined,
  PhoneOutlined, MailOutlined, DeleteOutlined,
  EyeOutlined, EditOutlined, CloseCircleOutlined,
  ExclamationCircleOutlined, CheckOutlined, SearchOutlined,
  LeftOutlined, RightOutlined
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import locale from 'antd/es/date-picker/locale/ru_RU';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.locale('ru');
dayjs.extend(relativeTime);

const API_URL = import.meta.env.VITE_API_URL || '';

// Создаем axios инстанс с токеном
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

// Месяцы на русском
const MONTHS_RU = {
  1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
  5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
  9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
};

const Events = () => {
  // Состояния
  const [events, setEvents] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [selectedHour, setSelectedHour] = useState(null);
  const [selectedQuarter, setSelectedQuarter] = useState(null);
  const [viewMode, setViewMode] = useState('month'); // month, day, hour
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('calendar');

  // Типы событий
  const eventTypes = {
    call: { label: '📞 Звонок', color: 'blue' },
    meeting: { label: '📅 Встреча', color: 'purple' },
    birthday: { label: '🎂 Поздравление', color: 'pink' },
    reminder: { label: '🔔 Напоминание', color: 'orange' },
    custom: { label: '📝 Своё', color: 'default' },
  };

  // Загрузка событий
  const fetchEvents = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/scheduled-events/');
      const eventsData = response.data.results || response.data;
      setEvents(eventsData);
    } catch (error) {
      console.error('❌ Ошибка загрузки:', error);
      message.error('Ошибка загрузки событий');
    } finally {
      setLoading(false);
    }
  };

  // Загрузка клиентов
  const fetchClients = async () => {
    try {
      const response = await api.get('/api/clients/');
      const clientsData = response.data.results || response.data;
      setClients(clientsData);
    } catch (error) {
      console.error('Ошибка загрузки клиентов:', error);
    }
  };

  useEffect(() => {
    fetchEvents();
    fetchClients();
  }, []);

  // Получение событий на день
  const getEventsForDay = (date) => {
    return events.filter(event => {
      const eventDate = dayjs(event.scheduled_date);
      return eventDate.isSame(date, 'day');
    });
  };

  // Получение событий на час
  const getEventsForHour = (date, hour) => {
    return events.filter(event => {
      const eventDate = dayjs(event.scheduled_date);
      return eventDate.isSame(date, 'day') && eventDate.hour() === hour;
    });
  };

  // Получение событий на четверть
  const getEventsForQuarter = (date, hour, minute) => {
    return events.filter(event => {
      const eventDate = dayjs(event.scheduled_date);
      return eventDate.isSame(date, 'day') && 
             eventDate.hour() === hour && 
             Math.floor(eventDate.minute() / 15) * 15 === minute;
    });
  };

  // Проверка наличия событий в день
  const hasEventsOnDay = (date) => {
    return events.some(event => dayjs(event.scheduled_date).isSame(date, 'day'));
  };

  // Проверка наличия событий в час
  const hasEventsOnHour = (date, hour) => {
    return events.some(event => {
      const eventDate = dayjs(event.scheduled_date);
      return eventDate.isSame(date, 'day') && eventDate.hour() === hour;
    });
  };

  // Создание события
const handleCreate = async (values) => {
  try {
    let scheduledDate;
    
    // Проверяем, пришли ли раздельные час и минута
    if (values.scheduled_hour !== undefined && values.scheduled_minute !== undefined) {
      scheduledDate = dayjs(values.scheduled_date)
        .hour(values.scheduled_hour)
        .minute(values.scheduled_minute)
        .second(0)
        .millisecond(0);
    } else {
      scheduledDate = values.scheduled_date;
    }
    
    const payload = {
      client: values.client_id,
      title: values.title,
      description: values.description || '',
      event_type: values.event_type,
      scheduled_date: scheduledDate.toISOString(),
    };
    
    await api.post('/api/scheduled-events/', payload);
    message.success('✅ Событие создано!');
    setModalVisible(false);
    form.resetFields();
    fetchEvents();
  } catch (error) {
    console.error('❌ Ошибка:', error);
    message.error('Ошибка при создании события');
  }
};

  // Отметка о выполнении
  const handleComplete = async (id) => {
    try {
      await api.post(`/api/scheduled-events/${id}/complete/`);
      message.success('✅ Событие отмечено как выполненное');
      fetchEvents();
      if (detailModalVisible) setDetailModalVisible(false);
    } catch (error) {
      console.error('❌ Ошибка:', error);
      message.error('Ошибка при выполнении');
    }
  };

  // Выполнить событие и создать следующее
const handleCompleteAndPlan = async (event) => {
  try {
    // 1. Отмечаем текущее событие как выполненное
    await api.post(`/api/scheduled-events/${event.id}/complete/`);
    message.success('✅ Событие выполнено!');
    
    // 2. Закрываем детали если открыты
    if (detailModalVisible) {
      setDetailModalVisible(false);
    }
    
    // 3. Обновляем список
    await fetchEvents();
    
    // 4. Открываем модалку создания следующего события
    const nextDate = dayjs(event.scheduled_date).add(1, 'day');
    
    // Ищем клиента в списке
    const client = clients.find(c => c.id === event.client);
    
    form.setFieldsValue({
      client_id: event.client,
      title: event.title,
      description: event.description || '',
      event_type: event.event_type,
      scheduled_date: nextDate,
    });
    
    // Показываем сообщение с подсказкой
    message.info(`📝 Создайте следующее событие для ${client?.first_name || 'клиента'}`);
    
    setModalVisible(true);
    } catch (error) {
        console.error('❌ Ошибка:', error);
        message.error('Ошибка при выполнении');
    }
};

  // Отмена выполнения
  const handleUncomplete = async (id) => {
    try {
      await api.post(`/api/scheduled-events/${id}/uncomplete/`);
      message.success('🔄 Событие отмечено как невыполненное');
      fetchEvents();
      if (detailModalVisible) setDetailModalVisible(false);
    } catch (error) {
      console.error('❌ Ошибка:', error);
      message.error('Ошибка');
    }
  };

  // Удаление события
  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/scheduled-events/${id}/`);
      message.success('🗑️ Событие удалено');
      fetchEvents();
      if (detailModalVisible) setDetailModalVisible(false);
    } catch (error) {
      console.error('❌ Ошибка:', error);
      message.error('Ошибка при удалении');
    }
  };

  // Открыть детали
  const showDetails = (record) => {
    setSelectedEvent(record);
    setDetailModalVisible(true);
  };

 // Открыть модалку создания с предзаполненной датой
    const showCreateModal = (date, hour, minute) => {
    let defaultDate = date || selectedDate;
    if (hour !== undefined) {
        defaultDate = defaultDate.hour(hour).minute(minute || 0);
    }
    form.resetFields();
    form.setFieldsValue({
        scheduled_date: defaultDate,
        scheduled_hour: defaultDate.hour(),
        scheduled_minute: Math.floor(defaultDate.minute() / 15) * 15, // Округляем до четверти
    });
    setModalVisible(true);
    };

  // Рендер календаря месяца
  const renderMonthCalendar = () => {
    const year = selectedDate.year();
    const month = selectedDate.month();
    const firstDay = dayjs().year(year).month(month).date(1);
    const daysInMonth = firstDay.daysInMonth();
    const startDayOfWeek = firstDay.day(); // 0 - воскресенье

    const weeks = [];
    let currentWeek = [];
    
    // Пустые ячейки в начале
    for (let i = 0; i < startDayOfWeek; i++) {
      currentWeek.push(null);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const currentDate = dayjs().year(year).month(month).date(day);
      const hasEvents = hasEventsOnDay(currentDate);
      const dayEvents = getEventsForDay(currentDate);
      const isToday = currentDate.isSame(dayjs(), 'day');
      const isPast = currentDate.isBefore(dayjs(), 'day');
      const isSelected = currentDate.isSame(selectedDate, 'day');

      currentWeek.push({
        day,
        date: currentDate,
        hasEvents,
        dayEvents,
        isToday,
        isPast,
        isSelected
      });

      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }

    // Добиваем пустыми ячейками
    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      weeks.push(currentWeek);
    }

    // Дни недели
    const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    // Переносим на понедельник
    const shiftedWeekDays = [...weekDays.slice(1), weekDays[0]];

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Button icon={<LeftOutlined />} onClick={() => changeMonth(-1)} />
          <h2 style={{ margin: 0 }}>
            {MONTHS_RU[month + 1]} {year}
          </h2>
          <Button icon={<RightOutlined />} onClick={() => changeMonth(1)} />
        </div>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: '4px'
        }}>
          {shiftedWeekDays.map((day, index) => (
            <div key={index} style={{ 
              textAlign: 'center', 
              fontWeight: 'bold', 
              padding: '8px',
              color: index >= 5 ? '#ff4d4f' : '#333'
            }}>
              {day}
            </div>
          ))}
          
          {weeks.map((week, weekIndex) => (
            week.map((day, dayIndex) => (
              <div 
                key={`${weekIndex}-${dayIndex}`}
                onClick={() => {
                  if (day && !day.isPast) {
                    setSelectedDate(day.date);
                    setViewMode('day');
                  }
                }}
                style={{
                  padding: '8px',
                  minHeight: '80px',
                  background: day ? (day.isSelected ? '#e6f7ff' : (day.hasEvents ? '#f0f5ff' : '#fff')) : 'transparent',
                  border: day?.isToday ? '2px solid #1890ff' : '1px solid #f0f0f0',
                  borderRadius: '4px',
                  cursor: day ? 'pointer' : 'default',
                  opacity: day?.isPast ? 0.5 : 1,
                  transition: 'all 0.2s',
                }}
              >
                {day && (
                  <>
                    <div style={{ 
                      fontWeight: day.isToday ? 'bold' : 'normal',
                      color: day.isPast ? '#ccc' : (day.hasEvents ? '#1890ff' : '#333')
                    }}>
                      {day.day}
                      {day.hasEvents && <span style={{ marginLeft: 4, color: '#1890ff' }}>•</span>}
                    </div>
                    <div style={{ fontSize: '10px', marginTop: 4 }}>
                      {day.dayEvents.slice(0, 2).map((event, idx) => (
                        <div key={idx} style={{ 
                          color: event.is_completed ? '#52c41a' : '#faad14',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {event.title}
                        </div>
                      ))}
                      {day.dayEvents.length > 2 && (
                        <div style={{ color: '#999', fontSize: '9px' }}>
                          +{day.dayEvents.length - 2} еще
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))
          ))}
        </div>
      </div>
    );
  };

  // Рендер дня (часы)
  const renderDayView = () => {
    const date = selectedDate;
    const dayEvents = getEventsForDay(date);
    
    // Группировка по часам
    const eventsByHour = {};
    for (let hour = 0; hour < 24; hour++) {
      eventsByHour[hour] = getEventsForHour(date, hour);
    }

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Button onClick={() => setViewMode('month')}>
            ⬅️ Назад к календарю
          </Button>
          <h2 style={{ margin: 0 }}>
            {date.format('D MMMM YYYY')}
          </h2>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => showCreateModal(date)}
          >
            Запланировать
          </Button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {Array.from({ length: 24 }, (_, hour) => {
            const hourEvents = eventsByHour[hour] || [];
            const hasEvents = hourEvents.length > 0;
            const isPast = date.isBefore(dayjs(), 'day') || 
                          (date.isSame(dayjs(), 'day') && hour < dayjs().hour());

            return (
              <div 
                key={hour}
                onClick={() => {
                  if (!isPast) {
                    setSelectedHour(hour);
                    setViewMode('hour');
                  }
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: hasEvents ? '#f0f5ff' : '#fafafa',
                  border: '1px solid #f0f0f0',
                  borderRadius: '4px',
                  cursor: isPast ? 'default' : 'pointer',
                  opacity: isPast ? 0.5 : 1,
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ width: '80px', fontWeight: 'bold' }}>
                  {String(hour).padStart(2, '0')}:00
                </div>
                <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {hasEvents ? (
                    hourEvents.map(event => (
                      <Tag 
                        key={event.id} 
                        color={event.is_completed ? 'green' : 'blue'}
                        onClick={(e) => {
                          e.stopPropagation();
                          showDetails(event);
                        }}
                      >
                        {event.title} ({event.client_full_name})
                      </Tag>
                    ))
                  ) : (
                    <span style={{ color: '#999' }}>Нет событий</span>
                  )}
                </div>
                <div style={{ marginLeft: 'auto', fontSize: '12px', color: '#999' }}>
                  {hasEvents ? `🔴 ${hourEvents.length} событий` : '⬜ свободно'}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Рендер часа (четверти)
  const renderHourView = () => {
    const date = selectedDate;
    const hour = selectedHour;
    
    // Четверти: 00, 15, 30, 45
    const quarters = [0, 15, 30, 45];
    
    const getQuarterEvents = (minute) => {
      return events.filter(event => {
        const eventDate = dayjs(event.scheduled_date);
        return eventDate.isSame(date, 'day') && 
               eventDate.hour() === hour && 
               Math.floor(eventDate.minute() / 15) * 15 === minute;
      });
    };

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Button onClick={() => setViewMode('day')}>
            ⬅️ Назад к дню
          </Button>
          <h2 style={{ margin: 0 }}>
            {date.format('D MMMM YYYY')} {String(hour).padStart(2, '0')}:00
          </h2>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => showCreateModal(date, hour)}
          >
            Запланировать
          </Button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
          {quarters.map(minute => {
            const quarterEvents = getQuarterEvents(minute);
            const hasEvents = quarterEvents.length > 0;
            const isPast = date.isBefore(dayjs(), 'day') || 
                          (date.isSame(dayjs(), 'day') && 
                           (hour < dayjs().hour() || 
                            (hour === dayjs().hour() && minute < Math.floor(dayjs().minute() / 15) * 15)));

            return (
              <Card
                key={minute}
                hoverable={!isPast}
                onClick={() => {
                  if (!isPast && !hasEvents) {
                    showCreateModal(date, hour, minute);
                  }
                }}
                style={{
                  background: hasEvents ? '#f0f5ff' : '#fff',
                  border: hasEvents ? '2px solid #1890ff' : '1px solid #f0f0f0',
                  opacity: isPast ? 0.5 : 1,
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                    {String(hour).padStart(2, '0')}:{String(minute).padStart(2, '0')}
                  </div>
                  <div style={{ fontSize: '12px', color: '#999', marginTop: 4 }}>
                    {hasEvents ? `🔴 ${quarterEvents.length} событий` : '⬜ Свободно'}
                  </div>
                  {hasEvents && (
                    <div style={{ marginTop: 8, textAlign: 'left' }}>
                      {quarterEvents.map(event => (
                        <div 
                          key={event.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            showDetails(event);
                          }}
                          style={{
                            padding: '4px 8px',
                            marginBottom: '4px',
                            background: event.is_completed ? '#f6ffed' : '#fff',
                            border: '1px solid #f0f0f0',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          <div><strong>{event.title}</strong></div>
                          <div style={{ color: '#666' }}>{event.client_full_name}</div>
                          <Tag color={event.is_completed ? 'green' : 'blue'} size="small">
                            {eventTypes[event.event_type]?.label}
                          </Tag>
                        </div>
                      ))}
                    </div>
                  )}
                  {!hasEvents && !isPast && (
                    <Button 
                      type="link" 
                      size="small"
                      onClick={() => showCreateModal(date, hour, minute)}
                    >
                      Запланировать
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    );
  };

  // Рендер активного вида
  const renderView = () => {
    switch(viewMode) {
      case 'month':
        return renderMonthCalendar();
      case 'day':
        return renderDayView();
      case 'hour':
        return renderHourView();
      default:
        return renderMonthCalendar();
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <h1 style={{ margin: 0, fontSize: '24px' }}>📅 Календарь событий</h1>
        <Space>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => showCreateModal(selectedDate)}
          >
            Создать событие
          </Button>
          {viewMode !== 'month' && (
            <Button onClick={() => setViewMode('month')}>
              📅 Месяц
            </Button>
          )}
        </Space>
      </div>

      <Card>
        <Spin spinning={loading}>
          {renderView()}
        </Spin>
      </Card>

      {/* Модалка создания события */}
    <Modal
    title="📅 Создать событие"
    open={modalVisible}
    onCancel={() => {
        setModalVisible(false);
        form.resetFields();
    }}
    footer={null}
    width={600}
    >
    <Form
        form={form}
        layout="vertical"
        onFinish={handleCreate}
    >
        <Row gutter={16}>
        <Col span={24}>
            <Form.Item
            name="client_id"
            label="Клиент"
            rules={[{ required: true, message: 'Выберите клиента' }]}
            >
            <Select
                showSearch
                placeholder="Выберите клиента"
                optionFilterProp="children"
            >
                {clients.map(client => (
                <Select.Option key={client.id} value={client.id}>
                    {client.first_name} {client.last_name} - {client.phone}
                </Select.Option>
                ))}
            </Select>
            </Form.Item>
        </Col>
        </Row>

        <Row gutter={16}>
        <Col span={24}>
            <Form.Item
            name="title"
            label="Заголовок"
            rules={[{ required: true, message: 'Введите заголовок' }]}
            >
            <Input placeholder="Введите заголовок события" />
            </Form.Item>
        </Col>
        </Row>

        <Row gutter={16}>
        <Col span={24}>
            <Form.Item
            name="description"
            label="Описание"
            >
            <Input.TextArea rows={3} placeholder="Введите описание (опционально)" />
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
            <Select placeholder="Выберите тип">
                {Object.entries(eventTypes).map(([key, value]) => (
                <Select.Option key={key} value={key}>{value.label}</Select.Option>
                ))}
            </Select>
            </Form.Item>
        </Col>
        <Col span={12}>
            <Form.Item
            name="scheduled_date"
            label="Дата и время"
            rules={[{ required: true, message: 'Выберите дату' }]}
            >
            <DatePicker
                showTime={{
                format: 'HH:mm',
                minuteStep: 15,  // Шаг 15 минут
                hourStep: 1,
                disabledMinutes: () => [],  // Разрешаем только 00, 15, 30, 45
                }}
                format="DD.MM.YYYY HH:mm"
                placeholder="Выберите дату и время"
                style={{ width: '100%' }}
                locale={locale}
                disabledTime={(current) => {
                // Запрещаем выбор произвольных минут
                return {
                    disabledMinutes: () => {
                    // Разрешаем только 00, 15, 30, 45
                    const disabled = [];
                    for (let i = 0; i < 60; i++) {
                        if (i % 15 !== 0) {
                        disabled.push(i);
                        }
                    }
                    return disabled;
                    }
                };
                }}
            />
            </Form.Item>
        </Col>
        </Row>

        <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
        <Space>
            <Button onClick={() => {
            setModalVisible(false);
            form.resetFields();
            }}>
            Отмена
            </Button>
            <Button type="primary" htmlType="submit">
            Создать
            </Button>
        </Space>
        </Form.Item>
    </Form>
    </Modal>

      {/* Модалка деталей события */}
      <Modal
        title={`📋 Детали события`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedEvent && (
          <div>
            {/* Статус */}
            <Alert
              message={selectedEvent.is_completed ? '✅ Выполнено' : '⏳ Ожидает выполнения'}
              type={selectedEvent.is_completed ? 'success' : 'info'}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ color: '#999', fontSize: 12 }}>Заголовок</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{selectedEvent.title}</div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ color: '#999', fontSize: 12 }}>Тип события</div>
                  <Tag color={eventTypes[selectedEvent.event_type]?.color}>
                    {eventTypes[selectedEvent.event_type]?.label}
                  </Tag>
                </div>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ color: '#999', fontSize: 12 }}>Клиент</div>
                  <div>
                    <UserOutlined /> {selectedEvent.client_full_name}
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ color: '#999', fontSize: 12 }}>Дата и время</div>
                  <div>
                    <CalendarOutlined /> {dayjs(selectedEvent.scheduled_date).format('DD.MM.YYYY HH:mm')}
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>
                    <ClockCircleOutlined /> {dayjs(selectedEvent.scheduled_date).fromNow()}
                  </div>
                </div>
              </Col>
            </Row>

            {selectedEvent.description && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ color: '#999', fontSize: 12 }}>Описание</div>
                <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                  {selectedEvent.description}
                </div>
              </div>
            )}

            <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              {!selectedEvent.is_completed && (
                <Button 
                  type="primary" 
                  icon={<CheckOutlined />}
                  onClick={() => handleComplete(selectedEvent.id)}
                >
                  Отметить выполненным
                </Button>
              )}
              {selectedEvent.is_completed && (
                <Button 
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => handleUncomplete(selectedEvent.id)}
                >
                  Отменить выполнение
                </Button>
              )}
              <Popconfirm
                title="Удалить событие?"
                description="Это действие нельзя отменить"
                onConfirm={() => handleDelete(selectedEvent.id)}
                okText="Да"
                cancelText="Нет"
              >
                <Button 
                  danger
                  icon={<DeleteOutlined />}
                >
                  Удалить
                </Button>
              </Popconfirm>
               {!selectedEvent.is_completed && (
    <>
      <Button 
        type="primary" 
        icon={<CheckOutlined />}
        onClick={() => {
          // Просто выполнить
          handleComplete(selectedEvent.id);
        }}
      >
        ✅ Выполнить
      </Button>
      <Button 
        type="primary" 
        ghost
        icon={<PlusOutlined />}
        onClick={() => {
          // Выполнить и запланировать следующее
          handleCompleteAndPlan(selectedEvent);
        }}
        style={{ borderColor: '#52c41a', color: '#52c41a' }}
      >
        🔄 Выполнить и запланировать
      </Button>
    </>
        )}
        {selectedEvent.is_completed && (
            <Button 
            danger
            icon={<CloseCircleOutlined />}
            onClick={() => handleUncomplete(selectedEvent.id)}
            >
            Отменить выполнение
            </Button>
        )}
        <Popconfirm
            title="Удалить событие?"
            description="Это действие нельзя отменить"
            onConfirm={() => handleDelete(selectedEvent.id)}
            okText="Да"
            cancelText="Нет"
        >
            <Button 
            danger
            icon={<DeleteOutlined />}
            >
            Удалить
            </Button>
        </Popconfirm>



            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Events;
import React, { useState, useEffect } from 'react'
import PlanEventModal from './PlanEventModal';
import {
  Table,
  Button,
  Input,
  Space,
  Tag,
  Modal,
  Form,
  Select,
  DatePicker,
  message,
  Popconfirm,
  Avatar,
  Card,
  Tooltip,
  Upload,
  Descriptions,
  Divider,
  Row,
  Col,
  Spin,
  Timeline,
} from 'antd'
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  EyeOutlined,
  UploadOutlined,
  CameraOutlined,
  CalendarOutlined,
  PhoneOutlined,
  MailOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CheckOutlined,
  TeamOutlined,
  StarOutlined,
} from '@ant-design/icons'
import axios from 'axios'
import dayjs from 'dayjs'
import './Clients.css'

const API_URL = import.meta.env.VITE_API_URL || ''

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

const { Option } = Select
const { TextArea } = Input

const ClientList = () => {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [cardModalVisible, setCardModalVisible] = useState(false)
  const [editingClient, setEditingClient] = useState(null)
  const [selectedClient, setSelectedClient] = useState(null)
  const [searchText, setSearchText] = useState('')
  const [form] = Form.useForm()
  const [tags, setTags] = useState([])
  const [avatarModalVisible, setAvatarModalVisible] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [cardLoading, setCardLoading] = useState(false)
  const [clientEvents, setClientEvents] = useState([])
  const [planModalVisible, setPlanModalVisible] = useState(false);
  const [planClient, setPlanClient] = useState(null);

  const statusMap = {
    vip: { color: 'gold', text: '⭐ VIP', icon: <StarOutlined /> },
    active: { color: 'green', text: '✅ Активный', icon: <CheckOutlined /> },
    regular: { color: 'blue', text: '🔄 Постоянный', icon: <TeamOutlined /> },
    lead: { color: 'orange', text: '🆕 Лид', icon: <UserOutlined /> },
    inactive: { color: 'red', text: '⏸️ Неактивный', icon: <CloseOutlined /> },
  }

  const handlePlanEvent = (client) => {
    setPlanClient(client);
    setPlanModalVisible(true);
  };

  useEffect(() => {
    fetchClients()
    fetchTags()
  }, [])

  const fetchClients = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/clients/')
      const data = response.data.results || response.data || []
      setClients(data)
    } catch (error) {
      console.error('Ошибка загрузки клиентов:', error)
      message.error('Ошибка загрузки клиентов')
    } finally {
      setLoading(false)
    }
  }

  const fetchTags = async () => {
    try {
      const response = await api.get('/api/tags/')
      const data = response.data.results || response.data || []
      setTags(data)
    } catch (error) {
      console.error('Ошибка загрузки тегов:', error)
    }
  }

  const fetchClientEvents = async (clientId) => {
    try {
      const response = await api.get(`/api/scheduled-events/?client=${clientId}`)
      const data = response.data.results || response.data || []
      setClientEvents(data)
    } catch (error) {
      console.error('Ошибка загрузки событий клиента:', error)
    }
  }

  const handleSearch = (value) => {
    setSearchText(value)
    api.get('/api/clients/', { params: { search: value } })
      .then((res) => {
        const data = res.data.results || res.data || []
        setClients(data)
      })
      .catch(() => {
        message.error('Ошибка поиска')
      })
  }

  const handleAdd = () => {
    setEditingClient(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingClient(record)
    form.setFieldsValue({
      ...record,
      birth_date: record.birth_date ? dayjs(record.birth_date) : null,
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/clients/${id}/`)
      message.success('Клиент удален')
      fetchClients()
    } catch (error) {
      message.error('Ошибка удаления')
    }
  }

  const handleSubmit = async (values) => {
    try {
      const data = {
        ...values,
        birth_date: values.birth_date ? values.birth_date.format('YYYY-MM-DD') : null,
      }
      
      if (editingClient) {
        await api.put(`/api/clients/${editingClient.id}/`, data)
        message.success('Клиент обновлен')
        setCardModalVisible(false)
      } else {
        await api.post('/api/clients/', data)
        message.success('Клиент добавлен')
      }
      
      setModalVisible(false)
      form.resetFields()
      fetchClients()
    } catch (error) {
      console.error('Ошибка сохранения:', error)
      message.error('Ошибка сохранения')
    }
  }

  const handleAvatarUpload = async (file) => {
    if (!selectedClient) return
    
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('avatar', file)
      await api.patch(`/api/clients/${selectedClient.id}/upload_avatar/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      message.success('Аватарка обновлена')
      setAvatarModalVisible(false)
      fetchClients()
      if (cardModalVisible) {
        fetchClientDetails(selectedClient.id)
      }
    } catch (error) {
      console.error('Ошибка загрузки аватарки:', error)
      message.error('Ошибка загрузки аватарки')
    } finally {
      setUploading(false)
    }
  }

  const fetchClientDetails = async (clientId) => {
    setCardLoading(true)
    try {
      const response = await api.get(`/api/clients/${clientId}/`)
      setSelectedClient(response.data)
      await fetchClientEvents(clientId)
    } catch (error) {
      console.error('Ошибка загрузки клиента:', error)
      message.error('Ошибка загрузки клиента')
    } finally {
      setCardLoading(false)
    }
  }

  const showClientCard = (record) => {
    fetchClientDetails(record.id)
    setCardModalVisible(true)
  }

    const getAvatarUrl = (avatar) => {
    if (!avatar) return null
    if (avatar.startsWith('http')) return avatar
    return `${API_URL}${avatar}`
  }

  const columns = [
    {
      title: 'Аватар',
      dataIndex: 'avatar',
      key: 'avatar',
      width: 80,
      render: (avatar, record) => (
        <Avatar 
          src={getAvatarUrl(avatar)}
          icon={!avatar && <UserOutlined />}
          size={50}
          style={{ cursor: 'pointer', border: '2px solid #e8e8e8' }}
          onClick={() => showClientCard(record)}
        />
      ),
    },
    {
      title: 'Имя',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: '500' }}>{record.first_name} {record.last_name}</div>
          {record.company && <div style={{ fontSize: '12px', color: '#999' }}>{record.company}</div>}
        </div>
      ),
      sorter: (a, b) => a.first_name.localeCompare(b.first_name),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
      render: (phone) => <a href={`tel:${phone}`}>{phone}</a>,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email) => email ? <a href={`mailto:${email}`}>{email}</a> : '—',
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
      filters: Object.entries(statusMap).map(([key, value]) => ({
        text: value.text,
        value: key,
      })),
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'В базе',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date) => {
        const days = dayjs().diff(dayjs(date), 'day')
        if (days < 1) return 'меньше дня'
        if (days < 7) return `${days} дн.`
        if (days < 30) return `${Math.floor(days / 7)} нед.`
        if (days < 365) return `${Math.floor(days / 30)} мес.`
        return `${Math.floor(days / 365)} г.`
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title="Просмотр карточки">
            <Button 
              icon={<EyeOutlined />} 
              size="small"
              onClick={() => showClientCard(record)}
            />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button 
              type="primary" 
              icon={<EditOutlined />} 
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Запланировать событие">
            <Button 
              type="primary" 
              ghost
              icon={<CalendarOutlined />}
              size="small"
              onClick={() => handlePlanEvent(record)}
            >
              План
            </Button>
          </Tooltip>
          <Popconfirm
            title="Удалить клиента?"
            description="Это действие нельзя отменить"
            onConfirm={() => handleDelete(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Tooltip title="Удалить">
              <Button danger icon={<DeleteOutlined />} size="small" />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="clients-page">
      <div className="page-header">
        <h1>👥 Клиенты</h1>
        <Space>
          <Input.Search
            placeholder="Поиск по имени, телефону, email..."
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить клиента
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={clients}
        rowKey="id"
        loading={loading}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `Всего ${total} клиентов`,
        }}
      />

      {/* Модалка создания/редактирования клиента */}
      <Modal
        title={editingClient ? 'Редактировать клиента' : 'Новый клиент'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="first_name"
            label="Имя"
            rules={[{ required: true, message: 'Введите имя' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item name="last_name" label="Фамилия">
            <Input />
          </Form.Item>
          
          <Form.Item name="middle_name" label="Отчество">
            <Input />
          </Form.Item>
          
          <Form.Item
            name="phone"
            label="Телефон"
            rules={[{ required: true, message: 'Введите телефон' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Введите корректный email' }]}>
            <Input />
          </Form.Item>
          
          <Form.Item name="company" label="Компания">
            <Input />
          </Form.Item>
          
          <Form.Item name="position" label="Должность">
            <Input />
          </Form.Item>
          
          <Form.Item name="birth_date" label="Дата рождения">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          
          <Form.Item name="status" label="Статус">
            <Select>
              <Option value="lead">Лид</Option>
              <Option value="active">Активный</Option>
              <Option value="regular">Постоянный</Option>
              <Option value="vip">VIP</Option>
              <Option value="inactive">Неактивный</Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="comment" label="Комментарий">
            <TextArea rows={3} />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingClient ? 'Сохранить' : 'Добавить'}
              </Button>
              <Button onClick={() => {
                setModalVisible(false)
                form.resetFields()
              }}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Модалка карточки клиента */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Avatar
              src={getAvatarUrl(selectedClient?.avatar)}
              icon={!selectedClient?.avatar && <UserOutlined />}
              size={48}
            />
            <div>
              <div style={{ fontSize: '18px', fontWeight: '600' }}>
                {selectedClient?.first_name} {selectedClient?.last_name}
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>
                {selectedClient?.company || 'Частное лицо'}
              </div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <Tag color={statusMap[selectedClient?.status]?.color || 'default'}>
                {statusMap[selectedClient?.status]?.text || selectedClient?.status}
              </Tag>
            </div>
          </div>
        }
        open={cardModalVisible}
        onCancel={() => {
          setCardModalVisible(false)
          setSelectedClient(null)
        }}
        footer={null}
        width={900}
        destroyOnClose
      >
        <Spin spinning={cardLoading}>
          {selectedClient && (
            <div>
              <Row gutter={16}>
                <Col span={24}>
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="Телефон">
                      <a href={`tel:${selectedClient.phone}`}>
                        <PhoneOutlined /> {selectedClient.phone}
                      </a>
                    </Descriptions.Item>
                    <Descriptions.Item label="Email">
                      {selectedClient.email ? (
                        <a href={`mailto:${selectedClient.email}`}>
                          <MailOutlined /> {selectedClient.email}
                        </a>
                      ) : '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Компания">
                      {selectedClient.company || '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Должность">
                      {selectedClient.position || '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Дата рождения">
                      {selectedClient.birth_date ? dayjs(selectedClient.birth_date).format('DD.MM.YYYY') : '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="В базе">
                      {dayjs(selectedClient.created_at).format('DD.MM.YYYY')}
                    </Descriptions.Item>
                    <Descriptions.Item label="Комментарий" span={2}>
                      {selectedClient.comment || 'Нет комментариев'}
                    </Descriptions.Item>
                  </Descriptions>
                </Col>
              </Row>

              <Divider orientation="left">
                <CalendarOutlined /> Запланированные события
              </Divider>

              {clientEvents.length > 0 ? (
                <Timeline>
                  {clientEvents.slice(0, 5).map(event => (
                    <Timeline.Item key={event.id} color={event.is_completed ? 'green' : 'blue'}>
                      <div>
                        <div style={{ fontWeight: '500' }}>{event.title}</div>
                        <div style={{ fontSize: '12px', color: '#999' }}>
                          <ClockCircleOutlined /> {dayjs(event.scheduled_date).format('DD.MM.YYYY HH:mm')}
                        </div>
                        <Tag color={event.is_completed ? 'green' : 'blue'} size="small">
                          {event.is_completed ? '✅ Выполнено' : '⏳ Ожидает'}
                        </Tag>
                        {event.description && (
                          <div style={{ fontSize: '12px', marginTop: 4 }}>{event.description}</div>
                        )}
                      </div>
                    </Timeline.Item>
                  ))}
                </Timeline>
              ) : (
                <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                  <CalendarOutlined style={{ fontSize: 32 }} />
                  <div style={{ marginTop: 8 }}>Нет запланированных событий</div>
                </div>
              )}

              <Divider />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setCardModalVisible(false)
                    handleEdit(selectedClient)
                  }}
                >
                  Редактировать
                </Button>
                <Button
                  type="primary"
                  ghost
                  icon={<CalendarOutlined />}
                  onClick={() => {
                    setCardModalVisible(false)
                    handlePlanEvent(selectedClient)
                  }}
                >
                  Запланировать событие
                </Button>
                <Button
                  icon={<CameraOutlined />}
                  onClick={() => {
                    setSelectedClient(selectedClient)
                    setAvatarModalVisible(true)
                  }}
                >
                  Сменить аватар
                </Button>
                <Popconfirm
                  title="Удалить клиента?"
                  description="Это действие нельзя отменить"
                  onConfirm={() => {
                    handleDelete(selectedClient.id)
                    setCardModalVisible(false)
                  }}
                  okText="Да"
                  cancelText="Нет"
                >
                  <Button danger icon={<DeleteOutlined />}>
                    Удалить
                  </Button>
                </Popconfirm>
              </div>
            </div>
          )}
        </Spin>
      </Modal>

      {/* Модалка аватарки */}
      <Modal
        title={`Аватарка: ${selectedClient?.first_name} ${selectedClient?.last_name}`}
        open={avatarModalVisible}
        onCancel={() => setAvatarModalVisible(false)}
        footer={null}
        width={400}
        centered
      >
        <div style={{ textAlign: 'center' }}>
          <Avatar
            src={getAvatarUrl(selectedClient?.avatar)}
            icon={!selectedClient?.avatar && <UserOutlined />}
            size={200}
            style={{ marginBottom: 20 }}
          />
          
          <Upload
            name="avatar"
            showUploadList={false}
            beforeUpload={(file) => {
              const isImage = file.type.startsWith('image/')
              if (!isImage) {
                message.error('Можно загружать только изображения!')
                return false
              }
              const isLt2M = file.size / 1024 / 1024 < 2
              if (!isLt2M) {
                message.error('Изображение должно быть меньше 2MB!')
                return false
              }
              handleAvatarUpload(file)
              return false
            }}
          >
            <Button icon={<UploadOutlined />} loading={uploading}>
              Загрузить новую аватарку
            </Button>
          </Upload>
          
          <div style={{ marginTop: 12, color: '#999', fontSize: 12 }}>
            <p>Поддерживаются форматы: JPG, PNG, GIF</p>
            <p>Максимальный размер: 2MB</p>
            <p>Рекомендуемый размер: 300x300</p>
          </div>
        </div>
      </Modal>

      {/* Модалка планирования события */}
      <PlanEventModal
        visible={planModalVisible}
        client={planClient}
        onClose={() => {
          setPlanModalVisible(false);
          setPlanClient(null);
        }}
        onSuccess={() => {
          if (cardModalVisible && selectedClient) {
            fetchClientEvents(selectedClient.id);
          }
          message.success('Событие создано!');
          fetchClients();
        }}
      />
    </div>
  )
}

export default ClientList

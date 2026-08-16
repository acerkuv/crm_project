import React, { useState, useEffect } from 'react'
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
} from '@ant-design/icons'
import axios from 'axios'
import dayjs from 'dayjs'
import './Clients.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
  const [editingClient, setEditingClient] = useState(null)
  const [searchText, setSearchText] = useState('')
  const [form] = Form.useForm()
  const [tags, setTags] = useState([])
  const [avatarModalVisible, setAvatarModalVisible] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)
  const [uploading, setUploading] = useState(false)

  const statusMap = {
    vip: { color: 'gold', text: 'VIP' },
    active: { color: 'green', text: 'Активный' },
    regular: { color: 'blue', text: 'Постоянный' },
    lead: { color: 'orange', text: 'Лид' },
    inactive: { color: 'red', text: 'Неактивный' },
  }

  useEffect(() => {
    fetchClients()
    fetchTags()
  }, [])

  const fetchClients = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/clients/')
      // ИСПРАВЛЕНО: берем results или сам массив
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
    } catch (error) {
      console.error('Ошибка загрузки аватарки:', error)
      message.error('Ошибка загрузки аватарки')
    } finally {
      setUploading(false)
    }
  }

  const getAvatarUrl = (avatar) => {
    if (!avatar) return null
    if (avatar.startsWith('http')) return avatar
    return `http://localhost:8000${avatar}`
  }

  const columns = [
    {
      title: 'Аватар',
      dataIndex: 'avatar',
      key: 'avatar',
      render: (avatar, record) => (
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <Avatar 
            src={getAvatarUrl(avatar)}
            icon={!avatar && <UserOutlined />}
            size={50}
            style={{ cursor: 'pointer', border: '2px solid #e8e8e8' }}
            onClick={() => {
              setSelectedClient(record)
              setAvatarModalVisible(true)
            }}
          />
          <CameraOutlined 
            style={{
              position: 'absolute',
              bottom: -2,
              right: -2,
              background: '#1890ff',
              color: 'white',
              borderRadius: '50%',
              padding: '2px',
              fontSize: '12px',
              cursor: 'pointer',
              border: '2px solid white',
            }}
            onClick={() => {
              setSelectedClient(record)
              setAvatarModalVisible(true)
            }}
          />
        </div>
      ),
    },
    {
      title: 'Имя',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (_, record) => `${record.first_name} ${record.last_name}`,
      sorter: (a, b) => a.first_name.localeCompare(b.first_name),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
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
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="Редактировать">
            <Button 
              type="primary" 
              icon={<EditOutlined />} 
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Удалить клиента?"
            description="Это действие нельзя отменить"
            onConfirm={() => handleDelete(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
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

      <Modal
        title={editingClient ? 'Редактировать клиента' : 'Новый клиент'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="first_name"
            label="Имя"
            rules={[{ required: true, message: 'Введите имя' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="last_name"
            label="Фамилия"
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="middle_name"
            label="Отчество"
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="phone"
            label="Телефон"
            rules={[{ required: true, message: 'Введите телефон' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: 'Введите корректный email' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="company"
            label="Компания"
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="position"
            label="Должность"
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="birth_date"
            label="Дата рождения"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          
          <Form.Item
            name="status"
            label="Статус"
          >
            <Select>
              <Option value="lead">Лид</Option>
              <Option value="active">Активный</Option>
              <Option value="regular">Постоянный</Option>
              <Option value="vip">VIP</Option>
              <Option value="inactive">Неактивный</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="comment"
            label="Комментарий"
          >
            <TextArea rows={3} />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingClient ? 'Сохранить' : 'Добавить'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

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
    </div>
  )
}

export default ClientList

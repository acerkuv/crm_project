import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Добавляем токен к запросам
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

// Обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const clientsApi = {
  list: (params) => api.get('/clients/', { params }),
  get: (id) => api.get(`/clients/${id}/`),
  create: (data) => api.post('/clients/', data),
  update: (id, data) => api.put(`/clients/${id}/`, data),
  delete: (id) => api.delete(`/clients/${id}/`),
  uploadAvatar: (id, file) => {
    const formData = new FormData()
    formData.append('avatar', file)
    return api.patch(`/clients/${id}/upload_avatar/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

export const tagsApi = {
  list: () => api.get('/tags/'),
  create: (data) => api.post('/tags/', data),
}

export const eventsApi = {
  list: () => api.get('/events/'),
  create: (data) => api.post('/events/', data),
  update: (id, data) => api.put(`/events/${id}/`, data),
  delete: (id) => api.delete(`/events/${id}/`),
}

export const statsApi = {
  get: () => api.get('/clients/'),
}

export default api

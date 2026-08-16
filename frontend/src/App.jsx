import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/Layout/MainLayout'
import Dashboard from './components/Dashboard/Dashboard'
import ClientList from './components/Clients/ClientList'
import Events from './components/Events/Events'

// Компонент логина (упрощенный)
const Login = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '100vh',
    background: '#f0f2f5'
  }}>
    <div style={{
      padding: 40,
      background: '#fff',
      borderRadius: 8,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      width: 400,
    }}>
      <h1 style={{ textAlign: 'center', marginBottom: 24 }}>🤗 CRM Уют</h1>
      <p style={{ textAlign: 'center', color: '#999' }}>
        Войдите с токеном из админки
      </p>
      <p style={{ 
        textAlign: 'center', 
        color: '#1890ff',
        fontSize: 12,
        wordBreak: 'break-all',
        background: '#f5f5f5',
        padding: 8,
        borderRadius: 4,
      }}>
        Токен: f8797e4768df850b9b9d4f1ca0e7b36dc9e2782f
      </p>
      <button 
        onClick={() => {
          localStorage.setItem('token', 'f8797e4768df850b9b9d4f1ca0e7b36dc9e2782f')
          localStorage.setItem('user', JSON.stringify({ first_name: 'Администратор' }))
          window.location.href = '/'
        }}
        style={{
          width: '100%',
          padding: '12px',
          background: '#1890ff',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          fontSize: 16,
          cursor: 'pointer',
        }}
      >
        Войти
      </button>
    </div>
  </div>
)

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/clients" element={<ClientList />} />
                  <Route path="/events" element={<Events />} />
                  <Route path="/statistics" element={<div style={{ padding: 24 }}>📊 Статистика (в разработке)</div>} />
                </Routes>
              </MainLayout>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
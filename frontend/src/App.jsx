import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/Layout/MainLayout'
import Dashboard from './components/Dashboard/Dashboard'
import ClientList from './components/Clients/ClientList'
import Events from './components/Events/Events'
import Statistics from './components/Statistics/Statistics'
import Plans from './components/Subscription/Plans'
import Login from './pages/Login'
import Profile from './components/Profile/Profile'  // ✅ Правильный импорт

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
                  <Route path="/statistics" element={<Statistics />} />
                  <Route path="/plans" element={<Plans />} />
                  <Route path="/profile" element={<Profile />} />  {/* ✅ Добавлен профиль */}
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
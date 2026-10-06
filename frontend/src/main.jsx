import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={ruRU}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 8,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        },
        components: {
          Layout: {
            siderBg: '#001529',
            headerBg: '#ffffff',
          },
          Card: {
            borderRadius: 12,
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)

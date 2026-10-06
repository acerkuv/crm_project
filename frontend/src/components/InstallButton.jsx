import React, { useState, useEffect } from 'react';
import { Button } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

const InstallButton = () => {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstall, setShowInstall] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setShowInstall(false);
      return;
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstall(true);
    };

    window.addEventListener('beforeinstallprompt', handler);
    window.addEventListener('appinstalled', () => setShowInstall(false));

    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const result = await deferredPrompt.userChoice;
    if (result.outcome === 'accepted') setShowInstall(false);
    setDeferredPrompt(null);
  };

  if (!showInstall) return null;

  return (
    <Button 
      type="primary" 
      icon={<DownloadOutlined />}
      onClick={handleInstall}
      style={{ marginBottom: 16 }}
      block
      size="large"
    >
      📱 Установить приложение
    </Button>
  );
};

export default InstallButton;

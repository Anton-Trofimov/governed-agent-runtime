import { useEffect, useState } from 'react';
import { App } from './App';
import { loadConfig, type AppConfig } from './config';

export function ConfiguredApp() {
  const [config, setConfig] = useState<AppConfig>();
  useEffect(() => {
    let active = true;
    void loadConfig().then(value => { if (active) setConfig(value); });
    return () => { active = false; };
  }, []);
  return config ? <App mode={config.mode} externalOrigin={config.origin}/> : <p role="status">Загрузка интерфейса…</p>;
}

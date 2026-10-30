import { useEffect, useState } from 'react';
import { App } from './App';
import { loadMode, type AppMode } from './config';

export function ConfiguredApp() {
  const [mode, setMode] = useState<AppMode>();
  useEffect(() => {
    let active = true;
    void loadMode().then(value => { if (active) setMode(value); });
    return () => { active = false; };
  }, []);
  return mode ? <App mode={mode}/> : <p role="status">Загрузка интерфейса…</p>;
}

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfiguredApp } from './ConfiguredApp';
import './style.css';
createRoot(document.getElementById('root')!).render(<StrictMode><ConfiguredApp/></StrictMode>);

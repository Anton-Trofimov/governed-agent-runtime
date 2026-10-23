import { useEffect, useState } from 'react';

export function AgentStatus({phase,label,since}:{phase:string;label:string;since?:string}){
  const [now,setNow]=useState(Date.now());
  useEffect(()=>{if(phase!=='running')return;const timer=window.setInterval(()=>setNow(Date.now()),1000);return()=>window.clearInterval(timer);},[phase]);
  const moving=phase==='preparing'||phase==='running';
  return <span className={'agent-status status-'+phase} role="status">
    <span className={'status-indicator'+(moving?' spinning':'')} aria-hidden="true"/>
    <span>{label}{phase==='running'&&since&&<small>Текущий шаг · {Math.max(0,Math.floor((now-Date.parse(since))/1000))} сек.</small>}</span>
  </span>;
}

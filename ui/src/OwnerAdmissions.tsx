import { useState } from 'react';
import { command, explainError, request } from './live';

export function OwnerAdmissions({enabled,connected,onChange}:{enabled:boolean;connected:boolean;onChange:(enabled:boolean)=>void}){
  const [pending,setPending]=useState(false);
  const [error,setError]=useState('');
  async function toggle(){
    setPending(true);setError('');
    const next=!enabled;
    try{
      const cmd=command('/api/admin/admissions','set_public_admissions',{enabled:next});
      await request(cmd.path,cmd.body);
      onChange(next);
    }catch(err){setError(explainError(err));}finally{setPending(false);}
  }
  return <section className="owner-admissions" aria-label="Личное управление доступом">
    <strong>Личный вход · свободный ввод</strong>
    <span>Новые публичные запуски: {enabled?'разрешены':'отключены'}</span>
    <button className="action" disabled={!connected||pending} onClick={()=>void toggle()}>{enabled?'Отключить новые публичные запуски':'Разрешить публичные запуски'}</button>
    <small>Текущий запуск продолжится. Оба входа используют один слот выполнения.</small>
    {error&&<p role="alert">{error}</p>}
  </section>;
}

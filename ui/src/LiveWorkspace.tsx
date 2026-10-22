import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, command, ensureSession, explainError, loadEvents, request, sessionSchema,
  snapshotSchema, statusSchema, type LiveEvent, type Session, type Snapshot } from './live';

type Props={onExit:()=>void;renderState:(s:Snapshot)=>ReactNode;renderCompact:(s:Snapshot)=>ReactNode};
const labels:Record<string,string>={preparing:'Подготовка',ready:'Готов к запросу',running:'Активен',
  awaiting_confirmation:'Ожидается решение',stopping:'Останавливается',terminal:'Завершён'};
export function LiveWorkspace({onExit,renderState,renderCompact}:Props){
  const [session,setSession]=useState<Session>();
  const [snapshot,setSnapshot]=useState<Snapshot>();
  const [events,setEvents]=useState<LiveEvent[]>([]);
  const [goal,setGoal]=useState('');
  const [error,setError]=useState('');
  const [connected,setConnected]=useState(false);
  const [busy,setBusy]=useState(false);
  const [seconds,setSeconds]=useState<number>();
  const [retry,setRetry]=useState(0);
  const [timedOut,setTimedOut]=useState(false);
  const eventsRef=useRef<LiveEvent[]>([]);
  const runRef=useRef<string|null>(null);
  const pending=useRef<ReturnType<typeof command>|null>(null);
  const mounted=useRef(true);
  const offset=useRef(0);
  const messages=useRef<HTMLDivElement>(null);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  // Read-only reconnect never resends a command. A fresh snapshot restores current state.
  useEffect(()=>{
    let active=true, timer:number, failedAt:number|undefined;
    setTimedOut(false);
    const poll=async()=>{
      try{
        const s=sessionSchema.parse(await request('/api/session'));
        let snap:Snapshot|undefined;
        if(s.current_run_id){
          snap=snapshotSchema.parse(await request(`/api/runs/${s.current_run_id}`));
          if(snap.run_id!==s.current_run_id)throw new Error('Foreign snapshot');
          let old=runRef.current===snap.run_id?eventsRef.current:[];
          try{old=await loadEvents(snap.run_id,old);}
          catch{old=await loadEvents(snap.run_id,[]);}
          if(!active)return;
          runRef.current=snap.run_id;eventsRef.current=old;setEvents(old);
          offset.current=Date.parse(snap.server_time)-Date.now();
        }
        if(!active)return;
        setSession(s);setSnapshot(snap);setConnected(true);failedAt=undefined;
        setError(current=>current==='Восстанавливаем связь…'?'':current);
        if(s.preparation_error)setError(s.preparation_error.message);
      }catch(err){
        if(!active)return;
        setConnected(false);
        if(err instanceof ApiError&&err.code==='SESSION_REQUIRED'){
          setSession(undefined);setSnapshot(undefined);setError('');
        }else{
          failedAt??=Date.now();setError('Восстанавливаем связь…');
          if(Date.now()-failedAt>=30000){setTimedOut(true);return;}
        }
      }
      if(active)timer=window.setTimeout(poll,1000);
    };
    void poll();
    return()=>{active=false;window.clearTimeout(timer);};
  },[retry]);
  useEffect(()=>{
    const update=()=>{
      const deadline=snapshot?.pending_confirmation?.expires_at??session?.reservation?.expires_at;
      setSeconds(deadline?Math.max(0,Math.ceil((Date.parse(deadline)-Date.now()-offset.current)/1000)):undefined);
    };
    update();const timer=window.setInterval(update,1000);return()=>window.clearInterval(timer);
  },[snapshot?.pending_confirmation?.expires_at,session?.reservation?.expires_at]);
  useEffect(()=>{if(messages.current)messages.current.scrollTop=messages.current.scrollHeight;},[events.length]);
  async function send(cmd:ReturnType<typeof command>){
    pending.current=cmd;setBusy(true);setError('');
    try{
      await request(cmd.path,cmd.body);pending.current=null;
      if(mounted.current)setRetry(x=>x+1);
    }catch(err){
      if(err instanceof ApiError)pending.current=null; // Known rejection, not ambiguous delivery.
      if(mounted.current)setError(explainError(err));
    }finally{if(mounted.current)setBusy(false);}
  }
  async function prepare(){
    setBusy(true);setError('');
    try{
      const status=statusSchema.parse(await request('/api/status'));
      if(status.availability!=='available')throw new ApiError(status.availability==='busy'?'LIVE_BUSY':'LIVE_UNAVAILABLE');
      setSession(await ensureSession());
      await send(command('/api/sessions','prepare'));
    }catch(err){setError(explainError(err));}finally{setBusy(false);}
  }
  const active=snapshot&&snapshot.phase!=='terminal';
  const pendingConfirmation=snapshot?.pending_confirmation;
  const canSubmit=!!session?.reservation&&!active&&connected&&!busy&&!pending.current&&
    session.reservation.phase!=='stopping';
  const currentEvents=events.filter(e=>!['phase_changed','model_status_changed'].includes(e.event_kind));
  const exit=async()=>{
    if(session?.reservation&&!active){
      await send(command('/api/session/release','release',{reservation_id:session.reservation.reservation_id}));
    }
    onExit();
  };
  return <>
    <aside className="scenario-note"><strong>Локальная проверка · имитатор модели</strong><p>Ответы формируются по тестовому сценарию. Реальная LLM не вызывается. Runtime выполняет настоящие проверки над моделируемой средой.</p></aside>
    <div className="workspace replaying live-workspace">
      {snapshot?.service_view?renderState(snapshot):<section className="state"><h2>Состояние системы</h2><p>Новый запуск ещё не начал наблюдение среды.</p></section>}
      <section className="chat" aria-label="Интерактивный диалог">
        {snapshot?.service_view&&renderCompact(snapshot)}
        <div className="chat-head"><div><h2>Агент управления сервисом</h2><div className="agent-controls"><span role="status">{labels[snapshot?.phase??session?.reservation?.phase??'']??'Готов к началу'}</span>{active&&<button className="live-stop" title="Остановить выполнение" aria-label="Остановить выполнение" disabled={!connected||busy||snapshot.stop_requested} onClick={()=>void send(command(`/api/runs/${snapshot.run_id}/stop`,'stop'))}>■</button>}</div></div></div>
        <div className="messages" ref={messages} aria-label="События интерактивного диалога">
          {currentEvents.filter(e=>['goal_accepted','proposal_recorded','operator_decision','confirmation_requested','run_finished'].includes(e.event_kind)).map(e=><article key={e.sequence} className={e.actor==='operator'?'user-message':'runtime-message'}><div className="author">{e.actor==='agent'?'Имитатор агента':e.actor==='operator'?'Оператор':'Runtime'}</div><EventText event={e}/></article>)}
          {!session?.reservation&&!active&&<button className="action primary" disabled={busy||!!pending.current} onClick={()=>void prepare()}>{snapshot?'Начать заново':'Начать локальный сценарий'}</button>}
          {snapshot?.terminal&&<section className="outcome"><h3>{snapshot.terminal.runtime_outcome?.rollback_completed?'Откат завершён':'Выполнение завершено'}</h3><p>{snapshot.terminal.explanation}</p><small>{snapshot.terminal.reason_code}</small><details><summary>Итоговый отчёт</summary><p>Имитатор модели · без LLM inference</p><p>Начальный запрос: {snapshot.goal}</p><p>Результат: {snapshot.terminal.reason_code}</p><p>Событий интерфейса: {events.length}</p><p>Наблюдение: {snapshot.service_view?.observation_id??'Не получено'}</p></details></section>}
        </div>
        {pendingConfirmation?<div className="live-input"><strong>{pendingConfirmation.action_summary}</strong><p>{pendingConfirmation.target_summary}</p><div className="buttons">{(['approve','reject'] as const).map(decision=><button className={'action '+(decision==='approve'?'primary':'')} key={decision} disabled={!connected||busy||!!pending.current||seconds===0||snapshot?.stop_requested} onClick={()=>void send(command(`/api/runs/${snapshot!.run_id}/decisions`,'decide',{confirmation_id:pendingConfirmation.confirmation_id,decision}))}>{decision==='approve'?'Подтвердить':'Отклонить'}</button>)}</div><small>Значимое действие требует явного подтверждения. Произвольный ввод на этом этапе ограничен платформой.</small>{seconds!==undefined&&<p>На решение: {seconds} сек.</p>}</div>:<form className="live-input" onSubmit={e=>{e.preventDefault();if(canSubmit&&goal.trim())void send(command('/api/runs','start_run',{reservation_id:session!.reservation!.reservation_id,goal}));}}>
          <div className="live-suggestions">{['Восстанови работу сервиса','После обновления сервис работает нестабильно. Восстанови его работу безопасным способом'].map(text=><button type="button" className="action" key={text} disabled={!canSubmit} onClick={()=>setGoal(text)}>{text}</button>)}</div>
          <label htmlFor="live-goal">Запрос агенту</label><textarea id="live-goal" value={goal} maxLength={2000} disabled={!canSubmit} onChange={e=>setGoal(e.target.value)}/><button className="action primary" disabled={!canSubmit||!goal.trim()}>Отправить</button>
          {session?.reservation?.phase==='preparing'&&<small>Подготовка. Можно отправить запрос сейчас — он дождётся готовности.</small>}
          {seconds!==undefined&&<p>На отправку запроса: {seconds} сек.</p>}
        </form>}
        {error&&<p role="alert" className="live-input">{error}</p>}
        {timedOut&&<button className="action" onClick={()=>setRetry(x=>x+1)}>Восстановить связь</button>}
        {pending.current&&!busy&&<button className="action" onClick={()=>void send(pending.current!)}>Проверить / повторить ту же команду</button>}
        <p className="translation-note">Имитатор выполняет фиксированный сценарий независимо от текста запроса. Ответы реальной модели здесь не оцениваются.</p>
        <button className="action" onClick={()=>void exit()}>К демонстрационным примерам</button>
      </section>
      <aside className="journal"><h2>Журнал runtime</h2><p className="subtle">События текущего локального запуска</p><ol>{currentEvents.filter(e=>e.actor==='runtime').map(e=><li key={e.sequence}><EventText event={e}/><small>Событие {e.sequence}</small></li>)}</ol></aside>
    </div>
  </>;
}
export function EventText({event:e}:{event:LiveEvent}){
  switch(e.event_kind){
    case 'goal_accepted':return <p>{e.payload.goal}</p>;
    case 'proposal_recorded':return <><p>{e.payload.proposal.rationale}</p><small>Оригинальное пояснение имитатора · {e.payload.proposal.tool_name}</small></>;
    case 'confirmation_requested':return <p>Требуется подтверждение: {e.payload.action_summary}.</p>;
    case 'operator_decision':return <p>{e.payload.decision==='approve'?'Оператор подтвердил':'Оператор отклонил'} предложенное действие.</p>;
    case 'admission_checked':return <><p>{e.payload.explanation} ({e.payload.result})</p><details><summary>Проверки runtime</summary><ul>{e.payload.checks.map(c=><li key={c.id}>{c.label}: {c.status}{c.reason?` · ${c.reason}`:''}</li>)}</ul></details></>;
    case 'tool_started':return <p>{e.payload.summary} ({e.payload.tool_name})</p>;
    case 'observation_accepted':return <p>Принято наблюдение {e.payload.observation_id}: {e.payload.healthy} Ready; восстановление — {e.payload.recovery.status}.</p>;
    case 'confirmation_resolved':return <p>Проверка подтверждения: {e.payload.status}.</p>;
    case 'run_finished':return <p>{e.payload.explanation} ({e.payload.reason_code})</p>;
    default:return null;
  }
}

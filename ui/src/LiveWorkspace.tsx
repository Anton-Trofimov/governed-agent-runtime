import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, command, ensureSession, explainError, loadEvents, request, sessionSchema,
  snapshotSchema, statusSchema, type LiveEvent, type Session, type Snapshot, type ServiceView } from './live';

type Props={onExit:()=>void;renderState:(s:ServiceView,unknown:boolean)=>ReactNode;renderCompact:(s:ServiceView,unknown:boolean)=>ReactNode};
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
  const reservationRef=useRef<string|null>(null);
  const lastServiceView=useRef<ServiceView|null>(null);
  const submittedDecision=useRef<string|null>(null);
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
        offset.current=Date.parse(s.server_time)-Date.now();
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
        if(!s.current_run_id){
          if(s.reservation?.reservation_id!==reservationRef.current){setGoal('');submittedDecision.current=null;}
          eventsRef.current=[];runRef.current=null;setEvents([]);
        }
        reservationRef.current=s.reservation?.reservation_id??null;
        if(s.reservation)lastServiceView.current=s.reservation.service_view;
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
      if(cmd.body.command==='decide')submittedDecision.current=String(cmd.body.confirmation_id);
      if(cmd.body.command==='start_run')setGoal('');
      if(cmd.body.command==='prepare'){
        setGoal('');setSnapshot(undefined);setEvents([]);eventsRef.current=[];runRef.current=null;
      }
      if(mounted.current)setRetry(x=>x+1);
      return true;
    }catch(err){
      if(err instanceof ApiError)pending.current=null; // Known rejection, not ambiguous delivery.
      if(mounted.current)setError(explainError(err));
      return false;
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
    session.reservation.phase!=='stopping'&&seconds!==0&&
    (!session.reservation.expires_at||Date.parse(session.reservation.expires_at)>Date.parse(session.server_time));
  const currentEvents=events.filter(e=>!['phase_changed','model_status_changed'].includes(e.event_kind));
  const serviceView=snapshot?.service_view??session?.reservation?.service_view??
    (session?.preparation_error?.code==='READY_EXPIRED'?lastServiceView.current:null);
  const unknown=!!snapshot?.terminal?.runtime_outcome?.unknown_write_effect;
  const blockedText=session?.preparation_error?.code==='READY_EXPIRED'?'Время ожидания запроса истекло. Начните сценарий заново.':!connected?'Восстанавливаем связь. Отправка временно недоступна.':
    snapshot?.phase==='terminal'?'Запуск завершён. Можно посмотреть результат или начать заново.':
    snapshot?.stop_requested?'Остановка запрошена. Ожидаем завершения текущего шага.':
    pendingConfirmation?'Ожидается ваше решение по действию выше.':
    snapshot?.phase==='preparing'?'Запрос принят. Ожидаем готовности модели.':
    active?'Агент готовит следующий шаг. Выполнение можно остановить.':
    'Для нового запроса начните сценарий.';
  return <>
    <div className="task-toolbar live-toolbar"><h1 id="task-heading">Восстановление сервиса <span className="service-name">payment-api</span></h1>
      <nav className="live-navigation" aria-label="Управление сценарием">
      <button className="action" disabled={busy} onClick={onExit}>К началу</button>
      {!session?.reservation&&!active&&<button className="action primary" disabled={busy||!!pending.current} onClick={()=>void prepare()}>{snapshot||session?.preparation_error?.code==='READY_EXPIRED'?'Начать заново':'Начать живой сценарий'}</button>}
      {error&&<p role="alert" className="admission-notice">{error}</p>}
      {timedOut&&<button className="action" onClick={()=>setRetry(x=>x+1)}>Восстановить связь</button>}
      {pending.current&&!busy&&<button className="action" onClick={()=>void send(pending.current!)}>Проверить / повторить ту же команду</button>}
      {active&&<small>К началу — экран выбора режима. Вы сможете вернуться к запуску.</small>}
    </nav></div>
    <div className="workspace replaying live-workspace">
      {serviceView?renderState(serviceView,unknown):<section className="state"><h2>Состояние системы</h2><p>{session?.preparation_error?.code==='READY_EXPIRED'?'Резерв сценария завершён. Начните заново, чтобы получить новое состояние.':'Получаем исходное состояние сценария…'}</p></section>}
      <section className="chat" aria-label="Интерактивный диалог">
        {serviceView&&renderCompact(serviceView,unknown)}
        <div className="chat-head"><div><h2>Агент управления сервисом<span className="simulator-label" title="Фиксированный тестовый сценарий независимо от текста запроса; LLM не вызывается.">Локальная проверка · имитатор модели</span></h2><div className="agent-controls"><span role="status">{session?.preparation_error?.code==='READY_EXPIRED'?'Время ожидания истекло':labels[snapshot?.phase??session?.reservation?.phase??'']??'Готов к началу'}</span>{active&&<button className="live-stop" title="Остановить выполнение" aria-label="Остановить выполнение" disabled={!connected||busy||snapshot.stop_requested||!!pending.current} onClick={()=>void send(command(`/api/runs/${snapshot.run_id}/stop`,'stop'))}>■</button>}</div></div></div>
        <div className="messages" ref={messages} aria-label="События интерактивного диалога">
          {currentEvents.filter(e=>['goal_accepted','proposal_recorded','operator_decision','confirmation_requested'].includes(e.event_kind)).map(e=>{
            const decision=e.event_kind==='operator_decision'?e:null;
            const context=decision?events.find(x=>x.event_kind==='confirmation_requested'&&x.payload.confirmation_id===decision.payload.confirmation_id):undefined;
            const confirmationEvent=e.event_kind==='confirmation_requested'?e:null;
            const awaiting=confirmationEvent&&pendingConfirmation?.confirmation_id===confirmationEvent.payload.confirmation_id&&
              submittedDecision.current!==confirmationEvent.payload.confirmation_id&&
              !events.some(x=>x.event_kind==='operator_decision'&&x.payload.confirmation_id===confirmationEvent.payload.confirmation_id);
            return <article key={e.sequence} className={e.actor==='operator'?'user-message':e.actor==='agent'?'agent-message':'runtime-message'}>
              <div className="author"><span className="actor-label">{e.actor==='agent'?'Агент · имитатор':e.actor==='operator'?'Оператор':'Runtime'}</span> · <time dateTime={e.occurred_at}>{new Date(e.occurred_at).toLocaleTimeString('ru-RU')}</time></div>
              {decision?<><div className="recorded-decision"><span className={'decision-choice '+(decision.payload.decision==='approve'?'approved':'rejected')}>{decision.payload.decision==='approve'?'✓ Подтверждено':'Отклонено'}</span></div><p>{context?.event_kind==='confirmation_requested'?context.payload.action_summary:'Решение по действию'}.</p></>:<EventText event={e}/>}
              {awaiting&&<div className="confirmation-actions"><p>{pendingConfirmation.target_summary}</p><div className="buttons">{(['approve','reject'] as const).map(choice=><button className={'action '+(choice==='approve'?'primary':'')} key={choice} disabled={!connected||busy||!!pending.current||seconds===0||snapshot?.stop_requested} onClick={()=>void send(command(`/api/runs/${snapshot!.run_id}/decisions`,'decide',{confirmation_id:pendingConfirmation.confirmation_id,decision:choice}))}>{choice==='approve'?'Подтвердить':'Отклонить'}</button>)}</div>{seconds!==undefined&&<small>На решение: {seconds} сек.</small>}</div>}
            </article>;
          })}
          {snapshot?.terminal&&<section className="outcome"><h3>{snapshot.terminal.runtime_outcome?.rollback_completed?'Откат завершён':'Выполнение завершено'}</h3><p>{snapshot.terminal.explanation}</p><small>{snapshot.terminal.reason_code}</small><details><summary>Итоговый отчёт</summary><p>Имитатор модели · без LLM inference</p><p>Начальный запрос: {snapshot.goal}</p><p>Результат: {snapshot.terminal.reason_code}</p><p>Событий интерфейса: {events.length}</p><p>Наблюдение: {snapshot.service_view?.observation_id??'Не получено'}</p></details></section>}
          {!snapshot&&session?.reservation&&<p className="empty-dialog">Исходное состояние сервиса доступно в панели состояния. Задайте цель агенту.</p>}
        </div>
        {session?.reservation&&!active?<form className="live-input" onSubmit={e=>{e.preventDefault();if(canSubmit&&goal.trim())void send(command('/api/runs','start_run',{reservation_id:session.reservation!.reservation_id,goal}));}}>
          <div className="live-suggestions">{['Восстанови работу сервиса','После обновления сервис работает нестабильно. Восстанови его работу безопасным способом'].map(text=><button type="button" className="action" key={text} disabled={!canSubmit} onClick={()=>setGoal(text)}>{text}</button>)}</div>
          <label htmlFor="live-goal">Запрос агенту</label><textarea id="live-goal" value={goal} maxLength={2000} disabled={!canSubmit} onChange={e=>setGoal(e.target.value)}/><div className="compose-actions"><button className="action primary" disabled={!canSubmit||!goal.trim()}>Отправить</button>{seconds!==undefined&&<small>На отправку: {seconds} сек.</small>}</div>
          {session.reservation.phase==='preparing'&&<small>Подготовка. Можно отправить запрос сейчас — он дождётся готовности.</small>}
        </form>:<div className={'live-input inactive-composer'+(pendingConfirmation?' awaiting-decision':'')}><textarea aria-label="Состояние диалога" disabled rows={2} value={blockedText}/></div>}

      </section>
      <aside className="journal"><h2>Журнал runtime</h2><p className="subtle">Проверки и выполнение · предложения агента — в чате</p><ol>{currentEvents.filter(e=>e.actor==='runtime').map(e=><li key={e.sequence}><EventText event={e}/><small>Событие {e.sequence}</small></li>)}</ol></aside>
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

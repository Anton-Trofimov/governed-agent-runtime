import { AgentStatus } from './AgentStatus';
import { LiveReport, TerminalCodes } from './LiveReport';
import { CompactComposer, ReportDialog, revealEvent } from './presentation';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, command, ensureSession, explainError, loadEvents, request, sessionSchema,
  snapshotSchema, statusSchema, providerLabel, type LiveEvent, type Session, type Snapshot, type ServiceView } from './live';

type Props={initialState?:ReactNode;onExit:()=>void;renderState:(s:ServiceView,unknown:boolean)=>ReactNode;renderCompact:(s:ServiceView,unknown:boolean)=>ReactNode};
const dialogueSuggestions=[
  {label:'Что ты умеешь?',text:'Что ты умеешь?',question:true},
  {label:'Почему сервис нестабилен?',text:'Почему сервис работает нестабильно?',question:true},
  {label:'Восстанови сервис',text:'Восстанови работу сервиса',question:false},
];
const labels:Record<string,string>={preparing:'Подготовка модели',ready:'Модель загружена. Агент готов к работе',running:'Агент выполняет задачу',
  awaiting_confirmation:'Ожидается решение оператора',stopping:'Останавливается',terminal:'Завершён'};
export function LiveWorkspace({onExit,renderState,renderCompact,initialState}:Props){
  const [session,setSession]=useState<Session>();
  const [snapshot,setSnapshot]=useState<Snapshot>();
  const [events,setEvents]=useState<LiveEvent[]>([]);
  const [goal,setGoal]=useState('');
  const [error,setError]=useState('');
  const [availability,setAvailability]=useState<'available'|'busy'|'unavailable'>();
  const [availabilityNotice,setAvailabilityNotice]=useState('');
  const [connectionError,setConnectionError]=useState('');
  const chat=useRef<HTMLElement>(null);
  const scrolledAdmission=useRef<string|null>(null);
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
  const input=useRef<HTMLTextAreaElement>(null);
  const journal=useRef<HTMLOListElement>(null);
  const followJournal=useRef(true);
  const [highlight,setHighlight]=useState<{sequence:number;side:'chat'|'journal'}>();
  useEffect(()=>{if(!highlight)return;const timer=window.setTimeout(()=>setHighlight(undefined),2000);return()=>window.clearTimeout(timer);},[highlight]);
  function reveal(sequence:number,side:'chat'|'journal'){
    const container=side==='chat'?messages.current:journal.current;
    const target=container?.querySelector<HTMLElement>(`[data-live-event="${sequence}"]`);
    if(!container||!target)return;
    if(side==='journal')followJournal.current=false;
    revealEvent(container,target);setHighlight({sequence,side});
  }
  useEffect(()=>{if(journal.current&&followJournal.current)journal.current.scrollTop=journal.current.scrollHeight;},[events.length]);
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
        setSession(s);setSnapshot(snap);
        if(!s.reservation&&(!snap||snap.phase==='terminal')){
          const status=statusSchema.parse(await request('/api/status'));
          if(!active)return;
          setAvailability(status.availability);
          setAvailabilityNotice(status.availability==='available'?'':explainError(new ApiError(status.unavailability_reason==='PUBLIC_PAUSED'?'PUBLIC_PAUSED':status.unavailability_reason==='SMOKE_LIMIT'?'SMOKE_LIMIT':status.availability==='busy'?'LIVE_BUSY':'LIVE_UNAVAILABLE')));
          if(status.availability==='available')setError('');
        }else{setAvailability(undefined);setAvailabilityNotice('');}
        setConnected(true);failedAt=undefined;setConnectionError('');
      }catch(err){
        if(!active)return;
        setConnected(false);
        if(err instanceof ApiError&&err.code==='SESSION_REQUIRED'){
          setSession(undefined);setSnapshot(undefined);
          try{
            const status=statusSchema.parse(await request('/api/status'));
            if(!active)return;
            setAvailability(status.availability);
            setAvailabilityNotice(status.availability==='available'?'':explainError(new ApiError(status.unavailability_reason==='PUBLIC_PAUSED'?'PUBLIC_PAUSED':status.unavailability_reason==='SMOKE_LIMIT'?'SMOKE_LIMIT':status.availability==='busy'?'LIVE_BUSY':'LIVE_UNAVAILABLE')));
            setConnected(true);setConnectionError('');failedAt=undefined;
            if(status.availability==='available')setError('');
          }catch{
            if(!active)return;
            setConnected(false);setConnectionError('Восстанавливаем связь…');
            failedAt??=Date.now();
            if(Date.now()-failedAt>=30000){setTimedOut(true);return;}
          }
        }else{
          failedAt??=Date.now();setConnectionError('Восстанавливаем связь…');
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
  useEffect(()=>{if(messages.current)messages.current.scrollTop=messages.current.scrollHeight;},[events.length,session?.dialogue?.messages.length]);
  async function send(cmd:ReturnType<typeof command>){
    pending.current=cmd;setBusy(true);setError('');
    try{
      await request(cmd.path,cmd.body);pending.current=null;
      if(cmd.body.command==='decide')submittedDecision.current=String(cmd.body.confirmation_id);
      if(cmd.body.command==='start_run'||cmd.body.command==='dialogue')setGoal('');
      if(cmd.body.command==='prepare'){
        scrolledAdmission.current=null;setGoal('');setSnapshot(undefined);setEvents([]);followJournal.current=true;eventsRef.current=[];runRef.current=null;
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
      if(status.availability!=='available')throw new ApiError(status.unavailability_reason==='PUBLIC_PAUSED'?'PUBLIC_PAUSED':status.unavailability_reason==='SMOKE_LIMIT'?'SMOKE_LIMIT':status.availability==='busy'?'LIVE_BUSY':'LIVE_UNAVAILABLE');
      setSession(await ensureSession());
      await send(command('/api/sessions','prepare'));
    }catch(err){setError(explainError(err));}finally{setBusy(false);}
  }
  const dialogue=session?.dialogue;
  const maxCalls=session?.input_policy?.max_calls??(session?.input_policy?.profile==='preset-only'?4:5);
  const thinking=dialogue?.state==='thinking';
  const queued=dialogue?.state==='preparing'&&dialogue.messages.at(-1)?.actor==='operator';
  const phase=snapshot?.phase??(thinking?'running':session?.reservation?.phase??(dialogue?.state==='terminal'?'terminal':''));
  const statusLabel=thinking?'Агент отвечает':dialogue?.state==='terminal'?(dialogue.reason==='DIALOGUE_EXPIRED'?'Время ожидания истекло':'Начальный диалог завершён'):(session?.preparation_error?.code==='READY_EXPIRED'||snapshot?.terminal?.reason_code==='CONFIRMATION_EXPIRED')?'Время ожидания истекло':
    session?.provider?.kind==='simulator'&&phase==='ready'?'Имитатор готов к работе':
    session?.provider?.kind==='simulator'&&phase==='preparing'?'Подготовка имитатора':labels[phase]??(availability==='busy'?'Живой режим занят':availability==='unavailable'?'Живой режим недоступен':'Готов к началу');
  const expired=dialogue?.reason==='DIALOGUE_EXPIRED'||session?.preparation_error?.code==='READY_EXPIRED'||snapshot?.terminal?.reason_code==='CONFIRMATION_EXPIRED';
  const notice=connectionError||availabilityNotice||error||session?.preparation_error?.message||'';
  const active=snapshot&&snapshot.phase!=='terminal';
  const admission=session?.reservation?.reservation_id??snapshot?.run_id;
  useEffect(()=>{
    if(window.innerWidth>620||!admission||notice||scrolledAdmission.current===admission)return;
    // A submitted goal belongs to the same admission: do not scroll again.
    if(scrolledAdmission.current&&snapshot?.run_id){scrolledAdmission.current=admission;return;}
    scrolledAdmission.current=admission;
    chat.current?.scrollIntoView?.({block:'start'});
  },[admission,notice,snapshot?.run_id]);
  const pendingConfirmation=snapshot?.pending_confirmation;
  const canSubmit=!!session?.reservation&&!active&&connected&&!busy&&!pending.current&&
    session.reservation.phase!=='stopping'&&!thinking&&!queued&&dialogue?.state!=='terminal'&&seconds!==0&&
    (!session.reservation.expires_at||Date.parse(session.reservation.expires_at)>Date.parse(session.server_time));
  useEffect(()=>{
    if(!input.current)return;
    input.current.style.height='auto';
    input.current.style.height=`${Math.min(120,Math.max(52,input.current.scrollHeight))}px`;
  },[goal,canSubmit]);
  const suggestions=dialogueSuggestions.filter(suggestion=>!suggestion.question||!dialogue?.messages.some((message,index)=>
    message.actor==='operator'&&message.text.trim().toLowerCase()===suggestion.text.toLowerCase()&&dialogue.messages[index+1]?.actor==='agent'));
  const currentEvents=events.filter(e=>!['phase_changed','model_status_changed'].includes(e.event_kind));
  const serviceView=snapshot?.service_view??session?.reservation?.service_view??dialogue?.service_view??
    (session?.preparation_error?.code==='READY_EXPIRED'?lastServiceView.current:null);
  const unknown=!!snapshot?.terminal?.runtime_outcome?.unknown_write_effect;
  const blockedText=availabilityNotice&&!connectionError?availabilityNotice:thinking?'Агент обрабатывает сообщение. Выполнение ещё не начато.':queued?'Запрос принят. Ожидаем готовности модели.':dialogue?.state==='terminal'?'Начальный диалог завершён. Можно посмотреть переписку или начать заново.':session?.preparation_error?.code==='READY_EXPIRED'?'Время ожидания запроса истекло. Начните сценарий заново.':!connected?'Восстанавливаем связь. Отправка временно недоступна.':
    snapshot?.phase==='terminal'?'Запуск завершён. Можно посмотреть результат или начать заново.':
    snapshot?.stop_requested?'Остановка запрошена. Ожидаем завершения текущего шага.':
    pendingConfirmation?'Ожидается ваше решение по действию выше.':
    snapshot?.phase==='preparing'?'Запрос принят. Ожидаем готовности модели.':
    active?'Агент готовит следующий шаг. Выполнение можно остановить.':
    'Для нового запроса начните сценарий.';
  return <>
    <div className="task-toolbar live-toolbar"><h1 id="task-heading">Восстановление <span className="desktop-word">сервиса </span><span className="service-name">payment-api</span></h1>
      <nav className="live-navigation" aria-label="Управление сценарием">
      <button className="action" disabled={busy} onClick={onExit}>К началу</button>
      {!session?.reservation&&!active&&<button className="action primary" disabled={busy||!!pending.current||!connected||availability!=='available'} onClick={()=>void prepare()}>{snapshot||dialogue?.state==='terminal'||session?.preparation_error?.code==='READY_EXPIRED'?'Начать заново':'Начать живой сценарий'}</button>}
      <button className="action chat-jump" onClick={()=>chat.current?.scrollIntoView?.({block:'start'})}>К чату ↓</button>
      {notice&&<p role="alert" className="admission-notice">{notice}</p>}
      {timedOut&&<button className="action" onClick={()=>setRetry(x=>x+1)}>Восстановить связь</button>}
      {pending.current&&!busy&&<button className="action" onClick={()=>void send(pending.current!)}>Проверить / повторить ту же команду</button>}
      {(active||session?.reservation)&&<small>К началу — экран выбора режима. Вы сможете вернуться к запуску.</small>}
    </nav></div>
    <div className="workspace replaying live-workspace">
      {serviceView?renderState(serviceView,unknown):initialState??<section className="state"><h2>Состояние системы</h2><p>{session?.preparation_error?.code==='READY_EXPIRED'?'Резерв сценария завершён. Начните заново, чтобы получить новое состояние.':'Получаем исходное состояние сценария…'}</p></section>}
      <section className="chat" ref={chat} aria-label="Интерактивный диалог">
        {serviceView&&renderCompact(serviceView,unknown)}
        <div className={"chat-head"+(phase==='preparing'&&session?.provider?.kind==='ollama'?' preparing-model':'')}><div><h2>Агент управления сервисом</h2><span className="simulator-label">{session?.provider?.kind==='ollama'?<>Локальная LLM<span className="model-separator"> · </span><span className="model-name">{session.provider.model_name}</span></>:providerLabel(session?.provider)}</span><div className="agent-controls"><AgentStatus phase={expired?'expired':phase} label={statusLabel} compactLabel={expired?'Время истекло':thinking?'Отвечает':session?.provider?.kind==='simulator'?undefined:({preparing:`Подготовка модели · ${session?.provider?.model_name??''}`,ready:'Агент готов',running:'Выполняется',awaiting_confirmation:'Ожидается решение'} as Record<string,string>)[phase]} hint={phase==='preparing'&&session?.provider?.kind!=='simulator'?'Первый запуск может занять несколько минут':undefined} since={events.filter(e=>e.event_kind==='model_status_changed'&&e.payload.model_status==='inference').at(-1)?.occurred_at}/>{session?.reservation&&dialogue&&<button className="live-stop" title="Завершить начальный диалог" aria-label="Завершить начальный диалог" disabled={!connected||busy||!!pending.current||dialogue.state==='terminal'} onClick={()=>void send(command('/api/session/release','release',{reservation_id:session.reservation!.reservation_id}))}>■</button>}{active&&<button className="live-stop" title="Остановить выполнение" aria-label="Остановить выполнение" disabled={!connected||busy||snapshot.stop_requested||!!pending.current} onClick={()=>void send(command(`/api/runs/${snapshot.run_id}/stop`,'stop'))}>■</button>}</div></div></div>
        <div className="messages" ref={messages} aria-label="События интерактивного диалога">
          {dialogue?.messages.map(message=><article key={message.id} className={message.actor==='operator'?'user-message':'agent-message'}><div className="author"><span className="actor-label">{message.actor==='operator'?'Оператор':session?.provider?.kind==='simulator'?'Агент · имитатор':'Агент'}</span> · <time dateTime={message.occurred_at}>{new Date(message.occurred_at).toLocaleString('ru-RU')}</time></div><p>{message.text}</p></article>)}
          {dialogue?.state==='terminal'&&<p role="status">{session?.preparation_error?.message??'Начальный диалог завершён. Выполнение не начато.'}</p>}
          {currentEvents.filter(e=>!(dialogue?.state==='admitted'&&e.event_kind==='goal_accepted')).filter(e=>['goal_accepted','proposal_recorded','operator_decision','confirmation_requested'].includes(e.event_kind)).map(e=>{
            const decision=e.event_kind==='operator_decision'?e:null;
            const context=decision?events.find(x=>x.event_kind==='confirmation_requested'&&x.payload.confirmation_id===decision.payload.confirmation_id):undefined;
            const confirmationEvent=e.event_kind==='confirmation_requested'?e:null;
            const awaiting=confirmationEvent&&pendingConfirmation?.confirmation_id===confirmationEvent.payload.confirmation_id&&
              submittedDecision.current!==confirmationEvent.payload.confirmation_id&&
              !events.some(x=>x.event_kind==='operator_decision'&&x.payload.confirmation_id===confirmationEvent.payload.confirmation_id);
            return <article key={e.sequence} data-live-event={e.sequence} data-highlight={highlight?.side==='chat'&&highlight.sequence===e.sequence} className={e.actor==='operator'?'user-message':e.actor==='agent'?'agent-message':'runtime-message'}>
              <div className="author"><span className="actor-label">{e.actor==='agent'?(session?.provider?.kind==='simulator'?'Агент · имитатор':'Агент'):e.actor==='operator'?'Оператор':'Runtime'}</span> · <time dateTime={e.occurred_at}>{new Date(e.occurred_at).toLocaleString('ru-RU')}</time></div>
              {decision?<><div className="recorded-decision"><span className={'decision-choice '+(decision.payload.decision==='approve'?'approved':'rejected')}>{decision.payload.decision==='approve'?'✓ Подтверждено':'Отклонено'}</span></div><p>{context?.event_kind==='confirmation_requested'?context.payload.action_summary:'Решение по действию'}.</p></>:<EventText event={e} simulator={session?.provider?.kind==='simulator'}/>}
              <LiveDetails event={e} events={events} onReveal={reveal}/>
              {awaiting&&<div className="confirmation-actions"><div className="buttons">{(['approve','reject'] as const).map(choice=><button className={'action '+(choice==='approve'?'primary':'')} key={choice} disabled={!connected||busy||!!pending.current||seconds===0||snapshot?.stop_requested} onClick={()=>void send(command(`/api/runs/${snapshot!.run_id}/decisions`,'decide',{confirmation_id:pendingConfirmation.confirmation_id,decision:choice}))}>{choice==='approve'?'Подтвердить':'Отклонить'}</button>)}</div>{seconds!==undefined&&<small>На решение: {seconds} сек.</small>}</div>}
            </article>;
          })}
          {snapshot?.terminal&&<section className="outcome"><h3>{snapshot.terminal.runtime_outcome?.rollback_completed?'Откат завершён':'Выполнение завершено'}</h3><p>{snapshot.terminal.explanation}</p><TerminalCodes terminal={snapshot.terminal}/><ReportDialog><p>{providerLabel(session?.provider)}</p><LiveReport snapshot={snapshot} events={events}/></ReportDialog></section>}
          {!snapshot&&session?.reservation&&!dialogue?.messages.length&&<p className="empty-dialog">Исходное состояние сервиса доступно в панели состояния. Задайте вопрос или цель агенту.</p>}
        </div>
        {session?.reservation&&!active&&!thinking&&!queued&&dialogue?.state!=='terminal'&&session.input_policy?.profile==='preset-only'?<div className="live-input">
          <div className="composer-heading"><span>Запрос агенту</span></div>
          <div className="live-suggestions preset-choices">{session.input_policy.choices.map(choice=><button type="button" className="action" key={choice.id} disabled={!canSubmit} onClick={()=>void send(command('/api/dialogue','dialogue',{reservation_id:session.reservation!.reservation_id,choice_id:choice.id}))}>{choice.label}</button>)}</div>
          <small>{session.provider?.kind==='simulator'?<strong>Тестовый режим: ответы имитатора заранее заданы. Реальная LLM не вызывается.</strong>:'Готовые запросы для безопасной демонстрации. Ответы и предложения формирует реальная LLM во время запуска.'}</small>
          <div className="compose-actions">{seconds!==undefined&&<small>На отправку: {seconds} сек.</small>}{dialogue&&<small>Обращения: {dialogue.calls}/{maxCalls}</small>}</div>
        </div>:session?.reservation&&!active&&!thinking&&!queued&&dialogue?.state!=='terminal'?<form className="live-input" onSubmit={e=>{e.preventDefault();if(canSubmit&&goal.trim())void send(dialogue?command('/api/dialogue','dialogue',{reservation_id:session.reservation!.reservation_id,text:goal}):command('/api/runs','start_run',{reservation_id:session.reservation!.reservation_id,goal}));}}>
          <div className="composer-heading"><label htmlFor="live-goal">Запрос агенту</label><div className="live-suggestions">{(dialogue?suggestions:[{label:'Восстанови работу сервиса',text:'Восстанови работу сервиса'},{label:'После обновления сервис работает нестабильно. Восстанови его работу безопасным способом',text:'После обновления сервис работает нестабильно. Восстанови его работу безопасным способом'}]).map(suggestion=><button type="button" className="action" key={suggestion.text} disabled={!canSubmit} onClick={()=>setGoal(suggestion.text)}>{suggestion.label}</button>)}</div></div>
          <textarea ref={input} rows={2} id="live-goal" value={goal} maxLength={2000} disabled={!canSubmit} onChange={e=>setGoal(e.target.value)}/><div className="compose-actions"><button className="action primary" disabled={!canSubmit||!goal.trim()}>Отправить</button>{seconds!==undefined&&<small>На отправку: {seconds} сек.</small>}{dialogue&&<><small>Обращения: {dialogue.calls}/{maxCalls}</small><small className={"dialogue-guidance"+(dialogue.calls===maxCalls-1?" last-call-warning":"")}>{dialogue.calls===maxCalls-1?<><span className="warning-symbol" aria-hidden="true">!</span> Осталось одно обращение</>:"Восстановление начнётся только по вашему запросу."}</small></>}</div>
          {dialogue&&session.provider?.kind==='simulator'&&<small>Имитатор отвечает по фиксированным примерам; понимание произвольного текста здесь не проверяется.</small>}
          {session.provider?.kind==='ollama'&&<small>Можно изменить подсказку: формулировка запроса может повлиять на результат. Ответ модели может быть на английском.</small>}
          {session.reservation.phase==='preparing'&&<small>Подготовка. Можно отправить запрос сейчас — он дождётся готовности.</small>}
        </form>:<div className={'live-input inactive-composer'+(pendingConfirmation?' awaiting-decision':'')}><CompactComposer text={blockedText}/></div>}

      </section>
      <aside className="journal"><h2>Журнал runtime</h2><p className="subtle">Проверки и выполнение · предложения агента — в чате</p><ol ref={journal} onScroll={()=>{const el=journal.current;if(el)followJournal.current=el.scrollHeight-el.clientHeight-el.scrollTop<32;}}>{currentEvents.filter(e=>e.actor==='runtime').map(e=><li key={e.sequence} data-live-event={e.sequence} data-highlight={highlight?.side==='journal'&&highlight.sequence===e.sequence}><EventText event={e} simulator={session?.provider?.kind==='simulator'}/><LiveDetails event={e} events={events} onReveal={reveal}/></li>)}</ol></aside>
    </div>
    {dialogue&&session?.input_policy?.profile!=='preset-only'&&<LastCallNotice key={dialogue.reservation_id} identity={dialogue.reservation_id} eligible={dialogue.calls===maxCalls-1&&dialogue.state==='ready'&&!!session?.reservation} onDismiss={()=>input.current?.focus()}/>}
  </>;
}

function LastCallNotice({identity,eligible,onDismiss}:{identity:string;eligible:boolean;onDismiss:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null);
  const storageKey='gar:last-call-dismissed';
  const [dismissed,setDismissed]=useState(()=>{
    try{return sessionStorage.getItem(storageKey)===identity;}catch{return false;}
  });
  useEffect(()=>{
    const node=dialog.current;
    if(eligible&&!dismissed){if(node&&!node.open)node.showModal();}
    else if(node?.open)node.close();
  },[eligible,dismissed]);
  function dismiss(){
    setDismissed(true);
    try{sessionStorage.setItem(storageKey,identity);}catch{/* In-memory dismissal still works. */}
    dialog.current?.close();
    onDismiss();
  }
  return <dialog ref={dialog} className="about-dialog last-call-dialog" aria-labelledby="last-call-title" aria-describedby="last-call-description" onCancel={e=>{e.preventDefault();dismiss();}}>
    <h2 id="last-call-title"><span className="warning-symbol" aria-hidden="true">!</span> Осталось одно обращение</h2>
    <p id="last-call-description">Можно задать последний вопрос или запросить восстановление сервиса. Если выбрать вопрос, после ответа начальный диалог завершится.</p>
    <p>Предлагаем запросить восстановление сервиса, чтобы пройти сценарий до конца.</p>
    <button type="button" className="action" autoFocus onClick={dismiss}>Понятно</button>
  </dialog>;
}

export function EventText({event:e,simulator=false}:{event:LiveEvent;simulator?:boolean}){
  switch(e.event_kind){
    case 'goal_accepted':return <p>{e.payload.goal}</p>;
    case 'proposal_recorded':return <><p className="subtle summary-label">Краткое объяснение, сформировано интерфейсом</p><p>Предложение агента: {e.payload.action_summary}.</p><p className="subtle original-label">{simulator?'Ответ агента · имитатор':'Ответ агента'}</p><p>{e.payload.proposal.rationale}</p></>;
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

export function LiveDetails({event,events,onReveal}:{event:LiveEvent;events:LiveEvent[];onReveal:(sequence:number,side:'chat'|'journal')=>void}){
  const related=events.filter(other=>other.run_id===event.run_id&&(
    event.event_kind==='proposal_recorded'&&other.event_kind==='admission_checked'&&other.payload.proposal_sequence===event.sequence||
    event.event_kind==='admission_checked'&&other.event_kind==='proposal_recorded'&&event.payload.proposal_sequence===other.sequence));
  return <details><summary>Подробнее</summary>
    <p className="subtle">Событие живого запуска: <code>event-{event.sequence}</code></p>
    {event.event_kind==='proposal_recorded'&&<p>Инструмент для предложенного действия: <code>{event.payload.proposal.tool_name}</code></p>}
    {related.map(other=><p className="event-link" key={other.sequence}>{other.event_kind==='proposal_recorded'?'Предложение агента':'Проверка runtime'}: <code>event-{other.sequence}</code> · <button className="text-link" onClick={()=>onReveal(other.sequence,other.event_kind==='proposal_recorded'?'chat':'journal')}>{other.event_kind==='proposal_recorded'?'Показать в чате':'Показать в журнале'}</button></p>)}
  </details>;
}

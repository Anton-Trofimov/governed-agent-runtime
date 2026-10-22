import { useEffect, useRef, useState } from 'react';
import { LiveWorkspace } from './LiveWorkspace';
import { request, statusSchema, sessionSchema } from './live';
import { loadRun, runs, readSelection, saveSelection, type Run, type Observation } from './data';

type Loader = (id: string) => Promise<Run>;
const timestamp = (value:string) => new Intl.DateTimeFormat('ru-RU', {dateStyle:'short', timeStyle:'medium',timeZone:'Europe/Moscow'}).format(new Date(value))+' МСК';

export function App({loader=loadRun}:{loader?:Loader}) {
  const help=useRef<HTMLDialogElement>(null);
  const helpButton=useRef<HTMLButtonElement>(null);
  const [live,setLive]=useState(false);
  const [availability,setAvailability]=useState<string>();
  useEffect(()=>{
    if(loader!==loadRun)return;
    let active=true;
    const inspect=async()=>{
      try{
        const status=statusSchema.parse(await request('/api/status'));
        if(active)setAvailability(status.availability);
      }catch{if(active)setAvailability(undefined);}
    };
    void inspect();
    request('/api/session').then(value=>{const session=sessionSchema.parse(value);if(active&&(session.current_run_id||session.reservation))setLive(true);}).catch(()=>{});
    const timer=window.setInterval(inspect,3000);
    return()=>{active=false;window.clearInterval(timer);};
  },[loader]);
  const [id,setId]=useState(readSelection);
  const [started,setStarted]=useState(false);
  const [result,setResult]=useState<{id:string;run?:Run;error?:boolean}>();
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    let active=true;
    saveSelection(id);
    loader(id).then(run=>{if(active)setResult({id,run});}).catch(()=>{if(active)setResult({id,error:true});});
    return ()=>{active=false;};
  },[id,loader,retry]);
  const current=result?.id===id?result:undefined;
  return <div id="operator-workspace">
    <header className="brandbar"><a href="#main" className="brand">Governed Agent<small>OPERATOR WORKSPACE</small></a><div className="platform-concept"><strong>Агентная платформа с разделением ответственности</strong><p className="responsibility-line">LLM предлагает · Runtime контролирует · Оператор задаёт цель и принимает решения</p></div><button className="help-trigger" ref={helpButton} onClick={()=>help.current?.showModal()} aria-haspopup="dialog">ⓘ Как это работает</button></header>
    <AboutDialog live={live} dialogRef={help} onClose={()=>helpButton.current?.focus()}/>
    <main id="main"><div className="context"><h1>Восстановление сервиса <span className="service-name">payment-api</span></h1></div>
      {started&&!live&&<div className="run-picker"><label htmlFor="run">Демонстрационный пример</label><select id="run" value={id} onChange={e=>setId(e.target.value)}>{runs.map(r=><option key={r.id} value={r.id}>{r.label}</option>)}</select></div>}
      {live?<LiveWorkspace onExit={()=>{setLive(false);setStarted(false);}} renderState={s=><StatePanel o={s.service_view!} live unknown={!!s.terminal?.runtime_outcome?.unknown_write_effect}/>} renderCompact={s=><CompactState o={s.service_view!} unknown={!!s.terminal?.runtime_outcome?.unknown_write_effect}/>}/>:!current?<p className="empty" role="status">Загрузка сохранённых данных…</p>:current.error||!current.run?<section className="empty" role="alert"><h2>Данные запуска недоступны</h2><p>Не удалось загрузить или проверить запись. Состояние системы не установлено.</p><button className="action" onClick={()=>{setResult(undefined);setRetry(x=>x+1);}}>Повторить загрузку</button></section>:<Workspace key={id} run={current.run} started={started} setStarted={setStarted} onLive={()=>setLive(true)} availability={availability}/>}
    </main>
    <footer className="page-notes"><p>{live?'В локальном тестовом режиме работает имитатор модели; LLM не вызывается.':'В живом режиме инференс LLM осуществляется на реальной AI-инфраструктуре.'}<br/>Условия работы сервиса payment-api и операции с ним моделируются.</p><p>Доступны сохранённые примеры; локальный интерактивный режим использует имитатор модели.</p><p className="project-credit">Проект Антона Трофимова · <a href="https://github.com/Anton-Trofimov/governed-agent-runtime">GitHub</a><br/>Разработано с участием AI-агентов по SDD Operating Model.</p></footer>
  </div>;
}

function Workspace({run,started,setStarted,onLive,availability}:{run:Run;started:boolean;setStarted:(value:boolean)=>void;onLive:()=>void;availability?:string}) {
  const [cursor,setCursor]=useState(0);
  const report=useRef<HTMLDetailsElement>(null);
  const journal=useRef<HTMLOListElement>(null);
  const messages=useRef<HTMLDivElement>(null);
  const events=run.replay.events;
  const visible=events.slice(0,cursor+1);
  const failureEvent=events.findIndex(e=>e.kind==='observation_applied'&&e.observation?.recovery.status==='FAIL')+1;
  const observation=[...visible].reverse().find(e=>e.observation)!.observation!;
  const done=started && cursor===events.length-1;
  useEffect(()=>{
    if(!started || cursor===0)return;
    const source=events[cursor].source;
    const item=messages.current?.querySelector<HTMLElement>(`[data-event-source="${source}"]`);
    if(item&&messages.current)messages.current.scrollTop+=item.getBoundingClientRect().top-messages.current.getBoundingClientRect().top;
    const log=journal.current?.querySelector<HTMLElement>(`[data-event-source="${source}"]`);
    if(log&&journal.current)journal.current.scrollTop+=log.getBoundingClientRect().top-journal.current.getBoundingClientRect().top;
  },[cursor,started,events]);
  const reset=()=>{setCursor(0);setStarted(false);};
  return <>
    {started&&failureEvent>0&&<aside className="scenario-note"><span className="scenario-symbol" aria-hidden="true">!</span><div><strong>Проверка восстановления не пройдена</strong><p>В этом примере специально смоделирована неудачная проверка после переноса трафика (событие {failureEvent} просмотра).</p><p>Он показывает, остановится ли агент без подтверждения восстановления и передаст ли дальнейшие действия оператору.</p></div></aside>}
    <div className={"workspace "+(started?"replaying":"")}>
      <StatePanel key={started?"playback":"welcome"} o={observation} final={done?run.view:undefined}/>
      <section className="chat" aria-label="Диалог с агентом">
        {started&&<CompactState o={observation} unknown={done&&run.view.unknown_write_effect}/>}
        <div className="chat-head"><div><h2>Агент управления сервисом</h2><div className="agent-controls"><span>{done?'Просмотр завершён':started?'Демонстрационный пример':'Готов к началу'}</span></div></div></div>
        {!started?<div className="welcome"><h3>Восстановите сервис payment-api после неудачного обновления.</h3><ul><li>Вы задаёте цель и подтверждаете изменения.</li><li>Агент оценивает состояние среды и предлагает действия.</li><li>Runtime проверяет условия и управляет выполнением.</li></ul><p className="choose-mode">Выберите режим</p><div className="buttons"><button className="action" disabled={availability!=='available'} onClick={onLive}>Начать живой сценарий</button><button className="action primary" onClick={()=>setStarted(true)}>Посмотреть пример</button></div><p className="subtle">{availability==='busy'?'Живой режим занят. Пока можно посмотреть демонстрационный пример.':availability==='available'?'Доступна локальная проверка с имитатором модели.':availability==='unavailable'?'Живой режим временно недоступен.':'Живой режим пока не подключён.'}</p></div>:<>
          <div className="messages" ref={messages} aria-label="События диалога">
            <article className="user-message illustrative-request"><div className="author">Запрос для демонстрации</div><p>Восстанови работу сервиса</p><small className="subtle">Формулировка для интерфейса. Исходный текст запроса в этой записи не сохранён.</small></article>
            {visible.filter(e=>['LLM','Оператор'].includes(e.actor)||['started','confirmation_pending','observation_applied','terminal','terminal_verified'].includes(e.kind)).map(e=><article key={e.source} data-event-source={e.source} className={e.actor==='Оператор'?'user-message':'runtime-message'}><div className="author">{e.actor==='LLM'?'Агент · предложение':e.actor} · {timestamp(e.at)}</div>{e.kind==='confirmation_consumed'&&<div className="recorded-decision"><small>Решение оператора в записи</small><div className="buttons"><button className="action selected-decision" disabled aria-pressed="true" aria-label="Подтвердить">✓ Подтвердить</button><button className="action" disabled aria-pressed="false">Отклонить</button></div></div>}<p><EventSummary text={e.summary} correctStop={failureEvent>0&&run.view.task_state==='SAFE_FALLBACK'}/></p>{e.actor==='LLM'&&<><p className="subtle summary-label">Краткое объяснение, сформировано интерфейсом</p><p className="subtle original-label">Оригинальное пояснение модели</p><p lang="en">{e.text}</p></>}<EventDetails event={e}/></article>)}
            {done&&<><Outcome run={run}/><button className="action" onClick={()=>{if(report.current){report.current.open=true;report.current.scrollIntoView?.({behavior:"smooth",block:"start"});}}}>Открыть итоговый отчёт</button></>}
          </div>
          <div className="playback" aria-label="Управление просмотром"><div className="event-counter"><span role="status">Событие {cursor+1} из {events.length}</span><RunSummary run={run}/></div><div className="buttons"><button className="action primary" disabled={done} onClick={()=>setCursor(n=>Math.min(n+1,events.length-1))}>Далее</button><button className="action" disabled={done} onClick={()=>setCursor(events.length-1)}>К результату</button><button className="action" onClick={reset}>К началу</button></div></div>
        </>}
        <p className="translation-note">{started&&<>Сохранённые события · без нового вызова модели.<br/></>}Ответ агента записан на английском. Для удобства можно включить перевод в браузере.</p>
      </section>
      <aside className="journal"><h2>Журнал runtime</h2><p className="subtle">Выбранные события записи</p>{started?<ol ref={journal}>{visible.filter(e=>e.actor==='Runtime').map(e=><li key={e.source} data-event-source={e.source}><time dateTime={e.at}>{timestamp(e.at)}</time><p><EventSummary text={e.summary} correctStop={failureEvent>0&&run.view.task_state==='SAFE_FALLBACK'}/></p><EventDetails event={e}/></li>)}</ol>:<p className="subtle">Ожидание просмотра примера</p>}</aside>
    </div>
    {done&&<details className="report" ref={report}><summary>Отчёт и источники</summary><pre>{run.report}</pre><p>{run.view.outcome_source} · {run.view.terminal_source}</p>{Object.entries(run.view.sources).map(([name,hash])=><p className="source" key={name}>{name} · SHA-256: {hash}</p>)}</details>}
  </>;
}

function StatePanel({o,final,live=false,unknown:explicitUnknown=false}:{o:Observation;final?:Run['view'];live?:boolean;unknown?:boolean}) {
  const [expanded,setExpanded]=useState(()=>typeof window.matchMedia==='function'?!window.matchMedia('(max-width:620px)').matches:true);
  const unknown=explicitUnknown||!!final?.unknown_write_effect;
  const recovered=!unknown&&!!o.shift_id&&o.shift_id===o.recovery.shift_id&&o.recovery.status==='PASS';
  const candidateRps=o.total_rps-o.stable_traffic_rps;
  const stableHealth=o.healthy===o.desired?'Healthy':'Scaling';
  const candidateHealth=o.candidate_count===0?'Удалена':candidateRps===0?'Без трафика':'Degraded';
  let incident=`Выявлена деградация версии ${o.candidate_version_id}: повышены доля ошибок и время ответа. Rollout версии ${o.candidate_version_id} приостановлен. Требуется восстановить работоспособность payment-api.`;
  let tone='incident-error';
  if(o.shift_id){incident=`На версии ${o.candidate_version_id} отсутствует трафик. Восстановление сервиса пока не подтверждено.`;tone='incident-pending';}
  if(o.recovery.status==='FAIL'){incident='Проверка восстановления завершилась с FAIL. Восстановление сервиса не подтверждено.';tone='incident-error';}
  if(recovered){incident=`Восстановление после переноса трафика подтверждено. Развёрнуто реплик версии ${o.candidate_version_id}: ${o.candidate_count}.`;tone='incident-pending';}
  if(final?.rollback_completed){incident='Работоспособность payment-api восстановлена. Откат завершён.';tone='incident-resolved';}
  if(unknown){incident='Исход изменения неизвестен. Последние данные до изменения с неизвестным исходом.';tone='incident-error';}
  return <section className="state" id="service-state" aria-labelledby="state-title"><div className="state-head"><h2 id="state-title">Состояние системы</h2></div><div className="version-summary"><div>{o.stable_version_id} · <span className={!unknown&&stableHealth==='Healthy'?'health-ok':''}><Changed value={unknown?'Неизвестно':stableHealth}/></span></div><div>{o.candidate_version_id} · <span className={candidateRps>0?'issue':''}><Changed value={unknown?'Неизвестно':candidateHealth}/></span></div></div><dl className="total-traffic"><div><dt>Общий трафик</dt><dd><Changed value={o.total_rps}/> RPS</dd></div></dl><p className={'incident-description '+tone}><Changed value={incident}/></p>
      <div className="versions"><h3>Версии и реплики</h3><div className="table-scroll"><table><thead><tr><th>Версия</th><th>Реплик</th><th>Состояние</th><th>RPS</th></tr></thead><tbody><tr><td>{o.stable_version_id}</td><td><Changed value={o.desired}/><small>Ready: <Changed value={o.healthy}/></small></td><td className={!unknown&&stableHealth==='Healthy'?'health-ok':''}><Changed value={unknown?'Неизвестно':stableHealth}/></td><td><Changed value={o.stable_traffic_rps}/></td></tr><tr><td>{o.candidate_version_id}</td><td><Changed value={o.candidate_count}/></td><td className={!unknown&&candidateRps>0?'issue':''}><Changed value={unknown?'Неизвестно':candidateHealth}/></td><td className={candidateRps>0?'issue':''}><Changed value={candidateRps}/></td></tr></tbody></table></div><p className="subtle">Ready — подтверждённые работоспособные реплики. Состояние отдельных реплик новой версии не установлено.</p></div>
      <details className="conditions" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}><summary>Условия безопасной работы</summary><ul><li>Безопасная производительность: 150 RPS на реплику.</li><li>Нагрузка ниже 90%, в том числе при потере одной реплики (N−1).</li><li>Расчёт UI для всего трафика на <Changed value={o.healthy}/> Ready: {o.healthy?(100*o.total_rps/(o.healthy*150)).toFixed(1)+'%':'нет мощности'}; N−1: {o.healthy>1?(100*o.total_rps/((o.healthy-1)*150)).toFixed(1)+'%':'нет мощности'}.</li></ul></details>
      {o.conflicting_operation&&<p className="issue">Обнаружена конфликтующая операция.</p>}<div className="state-foot">Последнее наблюдение<br/><time dateTime={o.observed_at}>{timestamp(o.observed_at)}</time><p>{live?'Последнее наблюдение моделируемой среды текущего запуска.':'Данные записи, не текущая проверка сервиса.'}</p></div>
    </section>;
}

function Outcome({run}:{run:Run}) {
  const v=run.view;
  const title=v.unknown_write_effect?'Исход изменения неизвестен':v.rollback_completed?'Откат завершён':'Выполнение остановлено';
  return <section className="outcome"><h3>{title}</h3><p>{v.unknown_write_effect?'Установите исход начатого изменения и актуальное состояние сервиса.':v.rollback_completed?'Завершение проверено runtime.':v.stop_reason==='MODEL_REQUESTED_STOP'?(run.view.task_state==='SAFE_FALLBACK'&&run.replay.events.some(e=>e.observation?.recovery.status==='FAIL')?'Агент корректно запросил остановку дальнейших действий; runtime завершил запуск. Дальнейшее восстановление сервиса — за оператором.':'Агент запросил остановку дальнейших действий, runtime завершил запуск. Восстановление сервиса необходимо обеспечить оператору.'):'Восстановление сервиса необходимо обеспечить самостоятельно.'}</p>{!v.rollback_completed&&<small className="source">Выполнение завершено: {v.task_state}{v.stop_reason?` · ${v.stop_reason}`:''}</small>}</section>;
}

function Changed({value}:{value:string|number}) {
  const previous=useRef(value);
  const [change,setChange]=useState<{from:string|number;to:string|number}|null>(null);
  useEffect(()=>{
    if(previous.current===value)return;
    setChange({from:previous.current,to:value});previous.current=value;
    const timer=window.setTimeout(()=>setChange(null),2000);
    return ()=>window.clearTimeout(timer);
  },[value]);
  return <span className={change?'value-changed':''} title={change?`${change.from} → ${change.to}`:undefined}>{value}</span>;
}
function EventSummary({text,correctStop=false}:{text:string;correctStop?:boolean}) {
  const explanation=text.includes('MODEL_REQUESTED_STOP')?`Агент ${correctStop?'корректно ':''}запросил остановку дальнейших действий; runtime завершил запуск. `+text:text;
  return <>{explanation.split(/(\bFAIL\b)/).map((part,i)=>part==='FAIL'?<strong className="failure-status" key={i}>{part}</strong>:part)}</>;
}
export function gateStatus(event:Run['replay']['events'][number],index:number) {
  const check=event.checks![index];
  if(check.status==='SKIPPED') {
    if(event.checks!.slice(0,index).some(c=>c.status==='FAILED'))return 'Не выполнялась: предыдущая проверка не пройдена';
    if(check.id==='G08_CONFIRMATION'&&['preflight','revalidation'].includes(event.kind))return 'Проверяется отдельно перед выполнением';
    return 'Не выполнялась на этом этапе';
  }
  return ({PASSED:'Пройдено',FAILED:'Не пройдено',NOT_APPLICABLE:'Не применяется'} as Record<string,string>)[check.status]??check.status;
}
function EventDetails({event}:{event:Run['replay']['events'][number]}) {
  return <details className="event-details"><summary>Подробнее</summary>
    {event.tool&&<p>Инструмент для предложенного действия: <code>{event.tool}</code></p>}
    {event.checks&&<ul>{event.checks.map((c,index)=><li key={c.id}>{c.label}: {gateStatus(event,index)} <code>({c.id} · {c.status})</code>{c.reason&&<span> · {c.reason}</span>}<small className="source">Правило проверки: {c.reference} · {c.id}</small></li>)}</ul>}
    <small className="source">Источник события в журнале выполнения: trace.jsonl · {event.source}</small>{event.reference&&<small className="source">{event.reference.includes("confirmation")?"Контракт подтверждения — привязка решения к конкретному действию":"Контракт инструмента — назначение, входные данные и результат"}: {event.reference}</small>}
  </details>;
}

function CompactState({o,unknown}:{o:Observation;unknown:boolean}) {
  const recovery=unknown?'Исход изменения неизвестен':o.recovery.status==='FAIL'?'Восстановление не подтверждено · FAIL':o.recovery.status==='PASS'&&!!o.shift_id&&o.shift_id===o.recovery.shift_id?'Восстановление подтверждено · PASS':o.shift_id?'Восстановление проверяется':'Восстановление не подтверждено';
  return <a className="compact-state" href="#service-state" aria-label="К полному состоянию сервиса"><span>{o.stable_version_id} · <Changed value={unknown?'данные до изменения':`${o.healthy} Ready`}/> · <Changed value={o.stable_traffic_rps}/> RPS</span><span>{o.candidate_version_id} · <Changed value={o.candidate_count}/> реплик · <Changed value={o.total_rps-o.stable_traffic_rps}/> RPS</span><strong><Changed value={recovery}/></strong></a>;
}

function AboutDialog({dialogRef,onClose,live}:{live:boolean;dialogRef:React.RefObject<HTMLDialogElement|null>;onClose:()=>void}) {
  return <dialog className="about-dialog" ref={dialogRef} onClose={onClose} aria-labelledby="about-title">
    <button className="action close-help" autoFocus onClick={()=>dialogRef.current?.close()}>Закрыть</button>
    <h2 id="about-title">От предложения модели — к контролируемому действию</h2>
    <p>Модель помогает выбрать следующий шаг. Платформа проверяет, допустим ли он, и управляет выполнением. Изменения требуют вашего явного подтверждения.</p>
    <h3>Как проходит работа</h3><ol>
      <li>Вы задаёте цель.</li>
      <li>Агент получает состояние среды и предлагает действие с пояснением.</li>
      <li>Runtime проверяет структуру предложения, полномочия, актуальность данных и условия выполнения.</li>
      <li>Перед изменением вы подтверждаете конкретное действие. Runtime повторно проверяет условия и запускает его.</li>
      <li>Результат проверяется, состояние обновляется, события сохраняются в журнале.</li>
    </ol>
    <h3>Почему это важно</h3><p>Убедительный ответ модели ещё не означает разрешение на действие. Подтверждение оператора тоже не отменяет проверки платформы. Журнал позволяет проследить, кто предложил и разрешил действие, чем подтверждён результат.</p>
    <p className="value-explanation">Такой подход полезен там, где важны надёжность, ответственность и прослеживаемость операций. В этом примере взаимодействие намеренно ограничено: оператор задаёт цель, затем явно подтверждает значимые изменения.</p>
    <div className="about-notes"><p>{live?'В локальном тестовом режиме работает имитатор модели; LLM не вызывается.':'В живом режиме инференс LLM осуществляется на реальной AI-инфраструктуре.'}<br/>Условия работы сервиса payment-api и операции с ним моделируются.</p><p>Доступны сохранённые примеры; локальный интерактивный режим использует имитатор модели.</p></div>
  </dialog>;
}

export function runCounts(run:Run) {
 const count=(kind:string)=>run.replay.events.filter(e=>e.kind===kind).length;
 return {proposals:count('model_output'),preflight:count('preflight'),revalidation:count('revalidation'),confirmations:count('confirmation_consumed')};
}
function RunSummary({run}:{run:Run}) {
 const n=runCounts(run);
 const count=(kind:string)=>run.replay.events.filter(e=>e.kind===kind).length;
 const remaining=run.replay.events.length-n.proposals-n.preflight-n.revalidation-n.confirmations-count('tool_call_started');
 return <details className="event-help" onKeyDown={e=>{if(e.key==='Escape'){e.currentTarget.open=false;e.currentTarget.querySelector('summary')?.focus();}}}>
   <summary aria-label="Состав событий" title="Состав событий">ⓘ</summary>
   <div className="run-summary"><div className="summary-heading"><strong>Состав событий: {run.replay.events.length}</strong><button className="action close-event-help" aria-label="Закрыть состав событий" title="Закрыть" onClick={e=>{const panel=e.currentTarget.closest('details')!;panel.open=false;panel.querySelector('summary')?.focus();}}>Закрыть</button></div>
     <p><b>Агент:</b> {n.proposals} предложений.</p>
     <p><b>Runtime:</b> {n.preflight+n.revalidation} проверок допуска — {n.preflight} предварительных и {n.revalidation} повторных перед выполнением.</p>
     <p><b>Оператор:</b> {n.confirmations} явных подтверждения; начальный запрос подготовлен для демонстрации.</p>
     <p><b>Вызовы инструментов:</b> {count('tool_call_started')}</p>
     <p><b>Остальные:</b> {remaining} — запросы подтверждения, принятые наблюдения, начало и завершение.</p>
   </div>
 </details>;
}

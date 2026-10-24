import type { LiveEvent, ServiceView, Snapshot } from './live';

export function LiveReport({snapshot,events}:{snapshot:Snapshot;events:LiveEvent[]}){
  const observations=events.filter(e=>e.event_kind==='observation_accepted');
  const initial=observations[0]?.payload;
  const final=snapshot.service_view;
  const decisions=events.filter(e=>e.event_kind==='operator_decision');
  const calls=events.filter(e=>e.event_kind==='tool_started');
  function state(view:ServiceView){return <>
    <p>Версия {view.stable_version_id}: {view.healthy} Ready из {view.desired} реплик · {view.stable_traffic_rps} RPS.</p>
    <p>Версия {view.candidate_version_id}: {view.candidate_count} реплик · {view.total_rps-view.stable_traffic_rps} RPS.</p>
    <p>Восстановление: {view.recovery.status} · наблюдение <code>{view.observation_id}</code> · {new Date(view.observed_at).toLocaleString('ru-RU')}</p>
  </>;}
  return <>
    <h3>Запрос оператора</h3><p>{snapshot.goal}</p>
    <h3>Результат</h3><p>{snapshot.terminal?.explanation}</p>{snapshot.terminal&&<TerminalCodes terminal={snapshot.terminal}/>}
    <h3>Исходное наблюдение</h3>{initial?state(initial):<p>Не получено.</p>}
    <h3>{snapshot.terminal?.runtime_outcome?.unknown_write_effect?'Последнее наблюдение — исход изменения неизвестен':'Последнее наблюдение'}</h3>{final?state(final):<p>Не получено.</p>}
    <h3>Решения оператора</h3>{decisions.length?<ul>{decisions.map(e=>{
      const request=events.find(x=>x.event_kind==='confirmation_requested'&&x.payload.confirmation_id===e.payload.confirmation_id);
      return <li key={e.sequence}>{e.payload.decision==='approve'?'Подтверждено':'Отклонено'}: {request?.event_kind==='confirmation_requested'?request.payload.action_summary:'Действие не установлено'} · {new Date(e.occurred_at).toLocaleString('ru-RU')} · event-{e.sequence}</li>;
    })}</ul>:<p>Решений не зарегистрировано.</p>}
    <h3>Вызовы инструментов</h3><p className="subtle">Начало вызова само по себе не подтверждает успешное изменение. Результат отражён в наблюдениях выше.</p>
    {calls.length?<ul>{calls.map(e=><li key={e.sequence}>{e.payload.summary} (<code>{e.payload.tool_name}</code>) · event-{e.sequence}</li>)}</ul>:<p>Вызовов не зарегистрировано.</p>}
  </>;
}

export function TerminalCodes({terminal}:{terminal:NonNullable<Snapshot['terminal']>}){
  const state=terminal.runtime_outcome?.task_state;
  const states:Record<string,string>={COMPLETED:'Завершена',SAFE_FALLBACK:'Безопасное завершение',FAILED:'Завершена с ошибкой'};
  const reasons:Record<string,string>={COMPLETED:'Выполнение завершено',CONFIRMATION_REJECTED:'Оператор отклонил действие',CONFIRMATION_EXPIRED:'Срок подтверждения оператором истёк',MODEL_REQUESTED_STOP:'Агент запросил остановку',UNKNOWN_WRITE_OUTCOME:'Исход изменения неизвестен'};
  return <div className="terminal-codes">
    {state&&<p>Состояние задачи: {states[state]??'Код runtime'} (<code>{state}</code>).</p>}
    <p>Причина завершения: {reasons[terminal.reason_code]??'Код платформы'} (<code>{terminal.reason_code}</code>).</p>
  </div>;
}

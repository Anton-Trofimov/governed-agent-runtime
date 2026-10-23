import { expect, it, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { LiveWorkspace } from './LiveWorkspace';
import { mergeEvents, snapshotSchema, command, request, ApiError } from './live';

afterEach(()=>vi.unstubAllGlobals());
const event={kind:'event',version:'live.v1',run_id:'run-1',sequence:1,
  occurred_at:'2026-10-22T12:00:00Z',event_kind:'goal_accepted',actor:'operator',payload:{goal:'Восстанови сервис'}};
const page={kind:'events',version:'live.v1',run_id:'run-1',events:[event],next_cursor:1,has_more:false};
it('deduplicates events and rejects gaps, foreign runs and false consent attribution',()=>{
  const first=mergeEvents([],page,'run-1');
  expect(mergeEvents(first,page,'run-1')).toEqual(first);
  expect(()=>mergeEvents([],{...page,events:[{...event,sequence:2}]},'run-1')).toThrow();
  expect(()=>mergeEvents([],{...page,run_id:'other'},'run-1')).toThrow();
  expect(()=>mergeEvents([],{...page,events:[{...event,actor:'agent'}]},'run-1')).toThrow();
});
it('does not automatically retry an ambiguous mutation',async()=>{
  const fetcher=vi.fn().mockRejectedValue(new TypeError('lost response'));
  vi.stubGlobal('fetch',fetcher);
  const cmd=command('/api/runs','start_run',{reservation_id:'reservation-1',goal:'text'});
  await expect(request(cmd.path,cmd.body)).rejects.toThrow();
  expect(fetcher).toHaveBeenCalledTimes(1);
});
it('reports a known server rejection separately',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({code:'LIVE_BUSY'})}));
  await expect(request('/api/sessions',{command:'prepare'})).rejects.toBeInstanceOf(ApiError);
});
const snapshot={kind:'snapshot',version:'live.v1',run_id:'run-1',phase:'terminal',runtime_state:'SAFE_FALLBACK',
  goal:'Восстанови сервис',model_status:'ready',service_view:null,pending_confirmation:null,
  stop_requested:false,terminal:{origin:'runtime',reason_code:'CONFIRMATION_EXPIRED',explanation:'Срок истёк',
    runtime_outcome:{task_state:'SAFE_FALLBACK',stop_reason:'CONFIRMATION_EXPIRED',rollback_completed:false,unknown_write_effect:false}},
  cursor:1,server_time:'2026-10-22T12:00:00Z'};
it('rejects a terminal snapshot without an outcome',()=>{
  expect(()=>snapshotSchema.parse({...snapshot,terminal:null})).toThrow();
});
it('restores an existing session read-only after mounting',async()=>{
  const fetcher=vi.fn(async(path:string)=>({ok:true,json:async()=>{
    if(path==='/api/session')return {kind:'session',provider:{kind:'simulator',model_name:null},version:'live.v1',session_id:'session-1',server_time:snapshot.server_time,reservation:null,
      current_run_id:'run-1',model_status:'ready',preparation_error:null};
    if(path.includes('/events?'))return page;
    return snapshot;
  }}));
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  await screen.findByRole('button',{name:'Начать заново'});
  await waitFor(()=>expect(screen.getByText('CONFIRMATION_EXPIRED')).toBeVisible());
  expect(fetcher.mock.calls.every((call)=>!String(call[0]).includes('/decisions'))).toBe(true);
  expect(fetcher.mock.calls.some(call=>call[0]==='/api/sessions')).toBe(false);
  expect(screen.getByRole('heading',{name:/Агент управления сервисом/})).toHaveTextContent('Локальная проверка · имитатор модели');
});

it('keeps only a disabled contextual composer after completion and exposes home navigation',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(path:string)=>({ok:true,json:async()=>
    path==='/api/session'?{kind:'session',provider:{kind:'simulator',model_name:null},version:'live.v1',session_id:'session-1',server_time:snapshot.server_time,reservation:null,
      current_run_id:'run-1',model_status:'ready',preparation_error:null}:path.includes('/events?')?page:snapshot})));
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  await screen.findByRole('button',{name:'Начать заново'});
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toHaveValue('Запуск завершён. Можно посмотреть результат или начать заново.');
  expect(screen.queryByRole('textbox',{name:'Запрос агенту'})).toBeNull();
  expect(screen.getByRole('button',{name:'К началу'})).toBeVisible();
});

const initialView={observation_id:'obs-0-0',observed_at:'2026-10-22T12:00:00Z',
  stable_version_id:'2.4.1',candidate_version_id:'2.4.2',desired:6,healthy:6,candidate_count:2,
  stable_traffic_rps:615,total_rps:820,safe_rps_per_replica:150,conflicting_operation:false,
  rollout_state:'PAUSED',shift_id:null,recovery:{status:'UNKNOWN',shift_id:null}};
const sessionBase={kind:'session',provider:{kind:'simulator',model_name:null},version:'live.v1',session_id:'session-1',server_time:snapshot.server_time,reservation:null,
  current_run_id:'run-1',model_status:'ready',preparation_error:null};
it('clears previous chat and journal only after successful new admission, before a goal',async()=>{
  let admitted=false;
  vi.stubGlobal('navigator',{locks:{request:async(_name:string,fn:()=>Promise<unknown>)=>fn()}});
  const fetcher=vi.fn(async(path:string,options?:RequestInit)=>{
    if(path==='/api/sessions'&&options?.method==='POST')admitted=true;
    return {ok:true,json:async()=>{
      if(path==='/api/status')return {kind:'status',version:'live.v1',availability:'available',model_status:'ready',server_time:snapshot.server_time};
      if(path==='/api/session')return admitted?{...sessionBase,current_run_id:null,reservation:{reservation_id:'fresh',phase:'ready',expires_at:null,service_view:initialView}}:sessionBase;
      if(path.includes('/events?'))return page;
      if(path==='/api/runs/run-1')return snapshot;
      return {kind:'ack'};
    }};
  });
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace onExit={()=>{}} renderState={s=><p>Версия: {s.candidate_version_id}</p>} renderCompact={()=>null}/>);
  await screen.findByRole('button',{name:'Начать заново'});
  expect(screen.getByText('Восстанови сервис',{exact:true})).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Начать заново'}));
  await screen.findByRole('textbox',{name:'Запрос агенту'});
  expect(screen.queryByText('Восстанови сервис',{exact:true})).toBeNull();
  expect(screen.getByRole('textbox',{name:'Запрос агенту'})).toHaveValue('');
  expect(screen.getByText('Версия: 2.4.2')).toBeVisible();
  expect(fetcher.mock.calls.some(([path,options])=>path==='/api/runs'&&options?.method==='POST')).toBe(false);
});
it('keeps confirmation in the runtime card and records an accepted choice once on the operator side',async()=>{
  let decided=false;
  const confirmation={confirmation_id:'confirm-1',created_at:snapshot.server_time,expires_at:'2099-10-22T12:05:00Z',
    action_summary:'Увеличить число реплик до 8',target_summary:'payment-api',rationale:'Capacity',
    expected_effect:'8 replicas',evidence_summary:'obs-0-0',parameters:[]};
  const confirmationEvent={...event,sequence:2,event_kind:'confirmation_requested',actor:'runtime',payload:confirmation};
  vi.stubGlobal('fetch',vi.fn(async(path:string,options?:RequestInit)=>{
    if(path.endsWith('/decisions')&&options?.method==='POST')decided=true;
    return {ok:true,json:async()=>{
      if(path==='/api/session')return sessionBase;
      if(path.includes('/events?'))return {...page,events:[event,confirmationEvent,...(decided?[{...event,sequence:3,event_kind:'operator_decision',payload:{confirmation_id:'confirm-1',decision:'approve'}}]:[])],next_cursor:decided?3:2};
      return {...snapshot,phase:decided?'running':'awaiting_confirmation',terminal:null,pending_confirmation:decided?null:confirmation};
    }};
  }));
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  const approve=await screen.findByRole('button',{name:'Подтвердить'});
  expect(approve.closest('article')).toHaveClass('runtime-message');
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  fireEvent.click(approve);
  const accepted=await screen.findByText('✓ Подтверждено');
  expect(accepted.closest('article')).toHaveClass('user-message');
  expect(within(accepted.closest('article')!).getByText('Увеличить число реплик до 8.')).toBeVisible();
  expect(screen.queryByRole('button',{name:'Подтвердить'})).toBeNull();
});

it('uses server time before a run even when browser clock is years ahead',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({...sessionBase,
    server_time:'2020-01-01T00:00:00Z',current_run_id:null,
    reservation:{reservation_id:'ready',phase:'ready',expires_at:'2020-01-01T00:05:00Z',service_view:initialView}})})));
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  await screen.findByRole('textbox',{name:'Запрос агенту'});
  expect(await screen.findByText('На отправку: 300 сек.')).toBeVisible();
});

it('disables goal submission at zero without creating a fresh reservation',async()=>{
  const fetcher=vi.fn(async(_path:string,_options?:RequestInit)=>({ok:true,json:async()=>({...sessionBase,
    server_time:'2020-01-01T00:05:00Z',current_run_id:null,
    reservation:{reservation_id:'ready',phase:'ready',expires_at:'2020-01-01T00:05:00Z',service_view:initialView}})}));
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  expect(await screen.findByRole('textbox',{name:'Запрос агенту'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Отправить'})).toBeDisabled();
  expect(fetcher.mock.calls.every(([,options])=>options?.method!=='POST')).toBe(true);
});

it('offers explicit restart after reservation expiry and keeps the composer disabled',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({...sessionBase,
    server_time:snapshot.server_time,current_run_id:null,
    preparation_error:{code:'READY_EXPIRED',message:'Время ожидания запроса истекло. Начните сценарий заново.'}})})));
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  await screen.findByRole('button',{name:'Начать заново'});
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  expect(screen.queryByRole('button',{name:'Отправить'})).toBeNull();
});

const proposalEvent={...event,sequence:2,event_kind:'proposal_recorded',actor:'agent',payload:{
  action_summary:'Проверить состояние реплик и трафика',proposal:{tool_name:'read_operational_status',rationale:'Оригинальный ответ'}}};
const checkEvent={...event,sequence:4,event_kind:'admission_checked',actor:'runtime',payload:{
  proposal_sequence:2,stage:'preflight',result:'ALLOW',explanation:'Проверено чтение состояния',checks:[]}};
it('links live proposal and admission in both directions and preserves journal reading position',async()=>{
  let items=[event,proposalEvent,{...event,sequence:3,event_kind:'model_status_changed',actor:'platform',payload:{model_status:'ready'}},checkEvent];
  vi.stubGlobal('fetch',vi.fn(async(path:string)=>({ok:true,json:async()=>
    path==='/api/session'?sessionBase:path.includes('/events?')?{...page,events:items,next_cursor:items.length}:snapshot})));
  const {container}=render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  const link=await screen.findByRole('button',{name:'Показать в журнале',hidden:true});
  fireEvent.click(link);
  const check=container.querySelector('.journal [data-live-event="4"]') as HTMLElement;
  expect(check).toHaveAttribute('data-highlight','true');
  expect(check).toHaveFocus();
  expect(check.querySelector('details')).toHaveAttribute('open');
  fireEvent.click(screen.getByRole('button',{name:'Показать в чате'}));
  expect(container.querySelector('.messages [data-live-event="2"]')).toHaveAttribute('data-highlight','true');
  expect(screen.getByText('Оригинальный ответ')).toBeVisible();
  expect(screen.getByText('Предложение агента: Проверить состояние реплик и трафика.')).toBeVisible();
  const journal=container.querySelector('.journal ol') as HTMLElement;
  Object.defineProperties(journal,{scrollHeight:{value:1000},clientHeight:{value:200}});
  journal.scrollTop=100;fireEvent.scroll(journal);
  items=[...items,{...checkEvent,sequence:5}];
  await waitFor(()=>expect(container.querySelector('.journal [data-live-event="5"]')).not.toBeNull(),{timeout:2000});
  expect(journal.scrollTop).toBe(100);
  journal.scrollTop=800;fireEvent.scroll(journal);
  items=[...items,{...checkEvent,sequence:6}];
  await waitFor(()=>expect(container.querySelector('.journal [data-live-event="6"]')).not.toBeNull(),{timeout:2000});
  expect(journal.scrollTop).toBe(1000);
});

it('uses server provider identity for real-model labels without sending commands',async()=>{
  const fetcher=vi.fn(async(path:string)=>({ok:true,json:async()=>{
    if(path==='/api/session')return {kind:'session',provider:{kind:'ollama',model_name:'qwen3.8:27b'},version:'live.v1',session_id:'session-1',server_time:snapshot.server_time,reservation:null,
      current_run_id:'run-1',model_status:'ready',preparation_error:null};
    if(path.includes('/events?'))return page;
    return snapshot;
  }}));
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  await screen.findByRole('button',{name:'Начать заново'});
  expect(screen.getByRole('heading',{name:/Агент управления сервисом/})).toHaveTextContent('Локальная LLM · qwen3.8:27b');
  expect(screen.queryByText(/имитатор/i)).not.toBeInTheDocument();
  expect(fetcher.mock.calls.every(call=>!String(call[0]).includes('/decisions'))).toBe(true);
});

it('explains exhausted smoke allowance without submitting another preparation',async()=>{
  const fetcher=vi.fn(async(path:string,_options?:RequestInit)=>({ok:true,json:async()=>{
    if(path==='/api/status')return {kind:'status',version:'live.v1',availability:'unavailable',unavailability_reason:'SMOKE_LIMIT',model_status:'ready',server_time:snapshot.server_time};
    if(path==='/api/session')return {kind:'session',version:'live.v1',session_id:'session-1',server_time:snapshot.server_time,reservation:null,current_run_id:'run-1',model_status:'ready',preparation_error:null};
    if(path.includes('/events?'))return page;
    return snapshot;
  }}));
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace onExit={()=>{}} renderState={()=>null} renderCompact={()=>null}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Начать заново'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Лимит запусков локальной проверки исчерпан');
  expect(fetcher.mock.calls.every(call=>!call[1]?.body)).toBe(true);
  expect(screen.getByRole('button',{name:'Открыть итоговый отчёт'})).toBeEnabled();
});

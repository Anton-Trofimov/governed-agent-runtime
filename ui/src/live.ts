import { z } from 'zod';

const text = z.string().min(1);
const count = z.number().int().nonnegative();
const model = z.enum(['unknown','preparing','ready','inference','unavailable']);
const observation = z.object({
  observation_id:text, observed_at:text, stable_version_id:text, candidate_version_id:text,
  desired:count, healthy:count, candidate_count:count, stable_traffic_rps:z.number().nonnegative(),
  total_rps:z.number().nonnegative(), safe_rps_per_replica:z.number().nonnegative(),
  conflicting_operation:z.boolean(), rollout_state:text, shift_id:text.nullable(),
  recovery:z.object({status:z.enum(['PASS','FAIL','PENDING','UNKNOWN']),shift_id:text.nullable()}),
});
const confirmation = z.object({
  confirmation_id:text, created_at:text, expires_at:text, action_summary:text,
  target_summary:text, rationale:text, expected_effect:text, evidence_summary:text,
  parameters:z.array(z.object({name:text,value:z.union([z.string(),z.number(),z.boolean(),z.null()])})),
});
const terminal = z.object({origin:z.enum(['platform','runtime']),reason_code:text,explanation:text,
  runtime_outcome:z.object({task_state:z.enum(['COMPLETED','SAFE_FALLBACK','FAILED']),
    stop_reason:text.nullable(),rollback_completed:z.boolean(),unknown_write_effect:z.boolean()}).nullable()});
const version = z.literal('live.v1');
export const statusSchema = z.object({kind:z.literal('status'),version,
  availability:z.enum(['available','busy','unavailable']),model_status:model,server_time:text});
export const sessionSchema = z.object({kind:z.literal('session'),version,session_id:text,
  reservation:z.object({reservation_id:text,phase:z.enum(['preparing','ready','stopping']),expires_at:text.nullable(),service_view:observation}).nullable(),
  current_run_id:text.nullable(),model_status:model,
  preparation_error:z.object({code:text,message:text}).nullable()});
export const snapshotSchema = z.object({kind:z.literal('snapshot'),version,run_id:text,
  phase:z.enum(['preparing','running','awaiting_confirmation','stopping','terminal']),
  runtime_state:text.nullable(),goal:text,model_status:model,service_view:observation.nullable(),
  pending_confirmation:confirmation.nullable(),stop_requested:z.boolean(),terminal:terminal.nullable(),
  cursor:count,server_time:text,
}).superRefine((s,ctx)=>{
  if ((s.phase==='terminal') !== !!s.terminal ||
      (s.phase==='awaiting_confirmation' && !s.pending_confirmation) ||
      (s.service_view && (s.service_view.healthy>s.service_view.desired ||
        s.service_view.stable_traffic_rps>s.service_view.total_rps)))
    ctx.addIssue({code:'custom',message:'Inconsistent live snapshot'});
});
const eventBase = {kind:z.literal('event'),version,run_id:text,sequence:count.positive(),occurred_at:text};
const eventSchema = z.discriminatedUnion('event_kind',[
  z.object({...eventBase,event_kind:z.literal('goal_accepted'),actor:z.literal('operator'),payload:z.object({goal:text})}),
  z.object({...eventBase,event_kind:z.literal('phase_changed'),actor:z.literal('platform'),payload:z.object({phase:text,reason:text})}),
  z.object({...eventBase,event_kind:z.literal('model_status_changed'),actor:z.literal('platform'),payload:z.object({model_status:model})}),
  z.object({...eventBase,event_kind:z.literal('proposal_recorded'),actor:z.literal('agent'),payload:z.object({proposal:z.object({tool_name:text,rationale:text})})}),
  z.object({...eventBase,event_kind:z.literal('admission_checked'),actor:z.literal('runtime'),payload:z.object({stage:text,result:text,explanation:text,
    checks:z.array(z.object({id:text,label:text,status:text,reason:text.nullable()}))})}),
  z.object({...eventBase,event_kind:z.literal('confirmation_requested'),actor:z.literal('runtime'),payload:confirmation}),
  z.object({...eventBase,event_kind:z.literal('operator_decision'),actor:z.literal('operator'),payload:z.object({confirmation_id:text,decision:z.enum(['approve','reject'])})}),
  z.object({...eventBase,event_kind:z.literal('confirmation_resolved'),actor:z.literal('runtime'),payload:z.object({confirmation_id:text,status:text,reason:text})}),
  z.object({...eventBase,event_kind:z.literal('tool_started'),actor:z.literal('runtime'),payload:z.object({tool_name:text,summary:text})}),
  z.object({...eventBase,event_kind:z.literal('observation_accepted'),actor:z.literal('runtime'),payload:observation}),
  z.object({...eventBase,event_kind:z.literal('stop_requested'),actor:z.literal('operator'),payload:z.object({})}),
  z.object({...eventBase,event_kind:z.literal('run_finished'),actor:z.literal('platform'),payload:terminal}),
]);
const pageSchema = z.object({kind:z.literal('events'),version,run_id:text,
  events:z.array(eventSchema).max(100),next_cursor:count,has_more:z.boolean()});
export type ServiceView = z.infer<typeof observation>;
export type Snapshot = z.infer<typeof snapshotSchema>;
export type LiveEvent = z.infer<typeof eventSchema>;
export type Session = z.infer<typeof sessionSchema>;
export type Status = z.infer<typeof statusSchema>;
export class ApiError extends Error {
  constructor(public code:string){super(code);}
}
export async function request(path:string, body?:Record<string,unknown>) {
  const response = await fetch(path,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',
    headers:body?{'Content-Type':'application/json','X-GAR-Request':'live.v1'}:undefined,
    body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(10000)});
  if(!response.ok){
    const error=await response.json().catch(()=>({code:'LIVE_UNAVAILABLE'}));
    throw new ApiError(typeof error.code==='string'?error.code:'LIVE_UNAVAILABLE');
  }
  return response.json();
}
export function command(path:string, command:string, fields:Record<string,unknown>={}):{path:string;body:Record<string,unknown>} {
  return {path,body:{command,command_id:crypto.randomUUID(),...fields}};
}
export async function ensureSession():Promise<Session> {
  if(!navigator.locks)throw new ApiError('BROWSER_LOCK_UNAVAILABLE');
  return navigator.locks.request('gar-session-bootstrap',async()=>{
    try{return sessionSchema.parse(await request('/api/session'));}
    catch(error){if(!(error instanceof ApiError)||error.code!=='SESSION_REQUIRED')throw error;}
    const cmd=command('/api/session/bootstrap','bootstrap');
    await request(cmd.path,cmd.body);
    return sessionSchema.parse(await request('/api/session'));
  });
}
export function mergeEvents(previous:LiveEvent[], page:unknown, runId:string):LiveEvent[] {
  const parsed=pageSchema.parse(page);
  if(parsed.run_id!==runId)throw new Error('Foreign event page');
  const result=[...previous];
  for(const event of parsed.events){
    if(event.run_id!==runId)throw new Error('Foreign event');
    if(event.sequence<=result.length)continue;
    if(event.sequence!==result.length+1)throw new Error('Event gap');
    result.push(event);
  }
  if(parsed.next_cursor!==result.length)throw new Error('Invalid event cursor');
  return result;
}
export async function loadEvents(runId:string, previous:LiveEvent[]) {
  let events=previous;
  for(let pages=0;pages<10;pages++){
    const page=pageSchema.parse(await request(`/api/runs/${runId}/events?after=${events.length}`));
    events=mergeEvents(events,page,runId);
    if(!page.has_more)return events;
  }
  throw new Error('Event page limit');
}
export function explainError(error:unknown){
  const code=error instanceof ApiError?error.code:'';
  return ({LIVE_BUSY:'Живой режим занят. Пока можно посмотреть демонстрационный пример.',
    LIVE_UNAVAILABLE:'Живой режим временно недоступен.',SESSION_REQUIRED:'Сессия завершена. Начните заново.',
    BROWSER_LOCK_UNAVAILABLE:'В этом браузере доступен только демонстрационный пример.',
    CONFIRMATION_EXPIRED:'Время подтверждения истекло.',ACTION_NOT_PENDING:'Это действие уже не ожидает решения.',
    SESSION_LIMIT:'Достигнут лимит локальной тестовой сессии.',
  } as Record<string,string>)[code]??'Связь прервалась. Состояние команды пока неизвестно; не отправляйте её заново.';
}

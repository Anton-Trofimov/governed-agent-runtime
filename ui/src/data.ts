import { z } from 'zod';
const count = z.number().int().nonnegative();
const text = z.string().min(1);
const observation = z.object({
  healthy: count, desired: count, candidate_count: count,
  stable_version_id: text, candidate_version_id: text,
  stable_traffic_rps: z.number().nonnegative(), total_rps: z.number().nonnegative(),
  conflicting_operation: z.boolean(), rollout_state: text,
  observed_at: z.string().datetime({offset: true}), observation_id: text,
  shift_id: text.nullable(),
  recovery: z.object({status: z.enum(['PASS','FAIL','UNKNOWN','PENDING']), shift_id: text.nullable()}),
});
const schema = z.object({
  replay: z.object({version: z.literal('2'), events: z.array(z.object({
    source: z.string().regex(/^event-\d+$/), at: z.string().datetime({offset:true}),
    kind: z.enum(['started','model_output','preflight','revalidation','confirmation_pending',
      'confirmation_consumed','tool_call_started','observation_applied','terminal','terminal_verified']),
    summary: text, reference: text.optional(),
    proposal_source: text.optional(), related_checks: z.array(text).optional(),
    checks: z.array(z.object({id:text,label:text,status:text,reason:text.nullable(),reference:text})).optional(),
    actor: z.enum(['Runtime','LLM','Оператор']), text, tool: text.optional(),
    observation: observation.nullable(),
  })).min(2)}),
  id: z.enum(['success','stop']), report: text,
  view: z.object({
    view_version: z.literal('1'), historical_only: z.literal(true),
    task_state: z.enum(['COMPLETED','SAFE_FALLBACK','FAILED']),
    stop_reason: text.nullable(), rollback_completed: z.boolean(), unknown_write_effect: z.boolean(),
    sources: z.object({'manifest.json': z.string().regex(/^[a-f0-9]{64}$/), 'trace.jsonl': z.string().regex(/^[a-f0-9]{64}$/)}),
    outcome_source: text, terminal_source: text,
    observation: z.object({value: observation, source: text}).nullable(),
    model_proposal: z.object({source: text, value: z.object({tool_name: text, rationale: text})}).nullable(),
  }),
}).superRefine(({view: v, replay}, ctx) => {
  const o = v.observation?.value;
  const events=replay.events;
  if(events.length<2) return;
  for(const event of events){
    if(event.proposal_source){
      const proposal=events.find(e=>e.source===event.proposal_source);
      if(!['preflight','revalidation'].includes(event.kind)||proposal?.kind!=='model_output'||!proposal.related_checks?.includes(event.source))ctx.addIssue({code:'custom',message:'Invalid proposal link'});
    }
    for(const source of event.related_checks??[]){
      const check=events.find(e=>e.source===source);
      if(event.kind!=='model_output'||check?.proposal_source!==event.source||!['preflight','revalidation'].includes(check.kind))ctx.addIssue({code:'custom',message:'Invalid check link'});
    }
  }
  const lastObservation=[...events].reverse().find(e=>e.observation)?.observation;
  if(events[0].kind!=='started' || !events[0].observation ||
     !['terminal','terminal_verified'].includes(events.at(-1)!.kind) ||
     events.some((e,i)=>(i>0 && Number(e.source.slice(6))<=Number(events[i-1].source.slice(6))) ||
       (!!e.observation !== ['started','observation_applied'].includes(e.kind)) ||
       (e.observation && (e.observation.stable_traffic_rps>e.observation.total_rps || e.observation.healthy>e.observation.desired))) ||
     JSON.stringify(lastObservation)!==JSON.stringify(o)) {
    ctx.addIssue({code:'custom',message:'Inconsistent recorded timeline'});
  }
  if (v.rollback_completed !== (v.task_state === 'COMPLETED') ||
      (v.rollback_completed && (v.unknown_write_effect || !o || o.candidate_count !== 0 || o.rollout_state !== 'ROLLED_BACK')) ||
      (o && (o.stable_traffic_rps > o.total_rps || o.healthy > o.desired))) {
    ctx.addIssue({code: 'custom', message: 'Contradictory saved outcome'});
  }
});
export type Observation = z.infer<typeof observation>;
export type Run = z.infer<typeof schema>;
export const runs = [{id:'success', label:'Откат завершён', ref:'BC-006 · run-001'}, {id:'stop', label:'Остановлено после проверки восстановления', ref:'BC-007 · run-001'}] as const;
export function parseRun(value: unknown, expectedId: string): Run {
  const run = schema.parse(value);
  if(run.id !== expectedId) throw new Error('Run identity mismatch');
  return run;
}
const key = 'governed-agent.viewer.v1.selected-run';
export function readSelection(): string {
  try { const id = localStorage.getItem(key); return runs.some(r => r.id === id) ? id! : 'success'; }
  catch { return 'success'; }
}
export function saveSelection(id: string) { try { localStorage.setItem(key, id); } catch { /* Optional preference only. */ } }
export async function loadRun(id: string): Promise<Run> {
  if(!runs.some(r=>r.id === id)) throw new Error('Unknown run');
  const response = await fetch(`${import.meta.env.BASE_URL}runs/${id}.json`);
  if(!response.ok) throw new Error('Run unavailable');
  return parseRun(await response.json(), id);
}
export function recoveryConfirmed(run: Run) {
  const o = run.view.observation?.value;
  return !run.view.unknown_write_effect && !!o?.shift_id && o.recovery.status === 'PASS' && o.shift_id === o.recovery.shift_id;
}
export function rationaleExcerpt(raw: string) {
  return raw.split(/(?<=[.;])\s+/).filter(s=>!(/\bwrites?\b/i.test(s) && /\b(budget|remain\w*)\b/i.test(s))).join(' ');
}

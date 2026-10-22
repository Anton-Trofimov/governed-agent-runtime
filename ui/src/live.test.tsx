import { expect, it, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
    if(path==='/api/session')return {kind:'session',version:'live.v1',session_id:'session-1',reservation:null,
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
  expect(screen.getByText('Локальная проверка · имитатор модели')).toBeVisible();
});

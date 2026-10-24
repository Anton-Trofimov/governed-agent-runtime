import { expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LiveReport } from './LiveReport';
import { snapshotSchema, type LiveEvent } from './live';

it('reports last observation without turning a started write into success',()=>{
  const observation={observation_id:'obs-before',observed_at:'2026-10-23T10:00:00Z',stable_version_id:'2.4.1',candidate_version_id:'2.4.2',desired:6,healthy:6,candidate_count:2,stable_traffic_rps:615,total_rps:820,safe_rps_per_replica:150,conflicting_operation:false,rollout_state:'PAUSED',shift_id:null,recovery:{status:'UNKNOWN' as const,shift_id:null}};
  const snapshot=snapshotSchema.parse({kind:'snapshot',version:'live.v1',run_id:'r',phase:'terminal',runtime_state:'FAILED',goal:'Восстановить сервис',model_status:'unavailable',service_view:observation,pending_confirmation:null,stop_requested:false,cursor:2,server_time:'2026-10-23T10:00:00Z',terminal:{origin:'runtime',reason_code:'UNKNOWN_WRITE_OUTCOME',explanation:'Исход изменения неизвестен.',runtime_outcome:{task_state:'FAILED',stop_reason:'UNKNOWN_WRITE_OUTCOME',rollback_completed:false,unknown_write_effect:true}}});
  const base={kind:'event' as const,version:'live.v1' as const,run_id:'r',occurred_at:'2026-10-23T10:00:00Z',actor:'runtime' as const};
  const events:LiveEvent[]=[{...base,sequence:1,event_kind:'observation_accepted',payload:observation},{...base,sequence:2,event_kind:'tool_started',payload:{tool_name:'scale_stable',summary:'Установить число реплик стабильной версии: 8'}}];
  render(<LiveReport snapshot={snapshot} events={events}/>);
  expect(screen.getByRole('heading',{name:'Последнее наблюдение — исход изменения неизвестен'})).toBeVisible();
  expect(screen.getByText(/Начало вызова само по себе/)).toBeVisible();
  expect(screen.getAllByText(/6 Ready из 6/)).toHaveLength(2);
  expect(screen.queryByText(/8 Ready/)).toBeNull();
});

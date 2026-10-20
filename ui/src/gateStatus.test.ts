import {expect,it} from 'vitest';
import {gateStatus} from './App';
import {parseRun} from './data';
import success from '../public/runs/success.json';
it('explains separate confirmation at both preflight and revalidation',()=>{
 const events=parseRun(success,'success').replay.events;
 for(const kind of ['preflight','revalidation']){
  const event=events.find(e=>e.kind===kind&&e.checks?.some(c=>c.id==='G08_CONFIRMATION'&&c.status==='SKIPPED'))!;
  expect(gateStatus(event,event.checks!.findIndex(c=>c.id==='G08_CONFIRMATION'))).toBe('Проверяется отдельно перед выполнением');
 }
});
it('distinguishes skipping after failure from the separate confirmation stage',()=>{
 const event=structuredClone(parseRun(success,'success').replay.events.find(e=>e.kind==='preflight')!);
 event.checks![6].status='FAILED';
 expect(gateStatus(event,7)).toBe('Не выполнялась: предыдущая проверка не пройдена');
});

import {runCounts} from './App';
import stop from '../public/runs/stop.json';
it('counts recorded proposals and admission rounds separately from confirmations',()=>{
 expect(runCounts(parseRun(success,'success'))).toEqual({proposals:5,preflight:5,revalidation:3,confirmations:3});
 expect(runCounts(parseRun(stop,'stop'))).toEqual({proposals:5,preflight:5,revalidation:2,confirmations:2});
});

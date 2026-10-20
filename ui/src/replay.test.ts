import { expect, it } from 'vitest';
import success from '../public/runs/success.json';
import { parseRun } from './data';
it('rejects an absent replay and unsupported replay version',()=>{
 const value=structuredClone(success) as any;
 delete value.replay;
 expect(()=>parseRun(value,'success')).toThrow();
 value.replay={version:'99'};
 expect(()=>parseRun(value,'success')).toThrow();
});
it('rejects an empty recorded timeline',()=>{
 const value=structuredClone(success) as any;
 value.replay={...value.replay,events:[]};
 expect(()=>parseRun(value,'success')).toThrow();
});

it('rejects reordered events and a final observation inconsistent with BC-009',()=>{
 const reordered=structuredClone(success);
 reordered.replay.events[1].source=reordered.replay.events[0].source;
 expect(()=>parseRun(reordered,'success')).toThrow();
 const mismatched=structuredClone(success);
 const last=[...mismatched.replay.events].reverse().find(e=>e.observation)!;
 last.observation!.total_rps+=1;
 expect(()=>parseRun(mismatched,'success')).toThrow();
});

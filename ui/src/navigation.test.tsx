import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { App } from './App';
import success from '../public/runs/success.json';
const time='2026-10-22T12:00:00Z';
const confirmation={confirmation_id:'c1',created_at:time,expires_at:'2026-10-22T12:05:00Z',action_summary:'Увеличить число реплик',target_summary:'payment-api',rationale:'capacity',expected_effect:'capacity',evidence_summary:'observed',parameters:[]};
const run={kind:'snapshot',version:'live.v1',run_id:'r1',phase:'awaiting_confirmation',runtime_state:null,goal:'Восстанови сервис',model_status:'ready',service_view:null,pending_confirmation:confirmation,stop_requested:false,terminal:null,cursor:0,server_time:time};
const session={kind:'session',version:'live.v1',session_id:'s1',server_time:time,reservation:null,current_run_id:'r1',model_status:'ready',preparation_error:null};
beforeEach(()=>{window.history.replaceState({garScreen:'home'},'','#home');localStorage.clear();});
afterEach(()=>vi.unstubAllGlobals());
function mockBackend({visitor=false,terminal=false,reservation=false}={}){
 let reserved=reservation;
 const fetcher=vi.fn(async(path:string,options?:RequestInit)=>({ok:true,json:async()=>{
  if(path.includes('/runs/success.json'))return success;
  if(path==='/api/status')return {kind:'status',version:'live.v1',availability:'busy',model_status:'ready',server_time:time};
  if(path==='/api/session/release'){reserved=false;return {};}
  if(path==='/api/session')return {...session,current_run_id:visitor||reservation?null:'r1',reservation:reserved?{reservation_id:'res1',phase:'ready',expires_at:confirmation.expires_at,service_view:success.replay.events.find(e=>e.observation)!.observation}:null};
  if(path.includes('/events?'))return {kind:'events',version:'live.v1',run_id:'r1',events:[],next_cursor:0,has_more:false};
  if(path==='/api/runs/r1')return terminal?{...run,phase:'terminal',pending_confirmation:null,terminal:{origin:'platform',reason_code:'CONFIRMATION_EXPIRED',explanation:'Время истекло',runtime_outcome:null}}:run;
  throw new Error(`Unexpected ${options?.method} ${path}`);
 }}));
 vi.stubGlobal('fetch',fetcher);return fetcher;
}
const mutations=(fetcher:ReturnType<typeof mockBackend>)=>fetcher.mock.calls.filter(([,options])=>options?.method==='POST');
it('lets the owner view a demo and return with the same deadline, without any new command',async()=>{
 const fetcher=mockBackend();render(<App/>);
 const banner=await screen.findByRole('complementary',{name:'Ваш запуск'});
 expect(banner).toHaveTextContent('На решение: 300 сек.');
 expect(screen.queryByText('Живой режим занят. Пока можно посмотреть демонстрационный пример.')).toBeNull();
 fireEvent.click(await screen.findByRole('button',{name:'Посмотреть пример'}));
 expect(banner).toBeVisible();
 fireEvent.click(within(banner).getByRole('button',{name:'Вернуться к запуску'}));
 await screen.findByText('Ожидается решение');
 fireEvent.click(screen.getByRole('link',{name:/Governed Agent/}));
 await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(mutations(fetcher)).toEqual([]);
});
it('keeps a visitor in recorded mode without offering another sessions run',async()=>{
 mockBackend({visitor:true});render(<App/>);
 await screen.findByText('Живой режим занят. Пока можно посмотреть демонстрационный пример.');
 expect(screen.getByRole('button',{name:'Начать живой сценарий'})).toBeDisabled();
 expect(screen.queryByRole('complementary',{name:'Ваш запуск'})).toBeNull();
 expect(screen.getByRole('button',{name:'Посмотреть пример'})).toBeEnabled();
});
it('opens a terminal result read-only and history transitions never start a run',async()=>{
 const fetcher=mockBackend({terminal:true});render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:'Посмотреть результат'}));
 await screen.findByText('Время истекло');
 window.history.replaceState({garScreen:'demo'},'','#demo');fireEvent.popState(window);
 await screen.findByRole('button',{name:'Далее'});
 window.history.replaceState({garScreen:'live'},'','#live');fireEvent.popState(window);
 await screen.findByText('Время истекло');
 expect(mutations(fetcher)).toEqual([]);
});
it('releases an unused reservation on browser history exit, without admitting another run',async()=>{
 window.history.replaceState({garScreen:'live'},'','#live');
 const fetcher=mockBackend({reservation:true});render(<App/>);
 await screen.findByRole('textbox',{name:'Запрос агенту'});
 window.history.replaceState({garScreen:'home'},'','#home');fireEvent.popState(window);
 await screen.findByRole('button',{name:'Посмотреть пример'});
 await waitFor(()=>expect(mutations(fetcher)).toHaveLength(1));
 expect(mutations(fetcher)[0][0]).toBe('/api/session/release');
});

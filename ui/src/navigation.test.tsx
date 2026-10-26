import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App } from './App';
import success from '../public/runs/success.json';
const time='2026-10-22T12:00:00Z';
const confirmation={confirmation_id:'c1',created_at:time,expires_at:'2026-10-22T12:05:00Z',action_summary:'Увеличить число реплик',target_summary:'payment-api',rationale:'capacity',expected_effect:'capacity',evidence_summary:'observed',parameters:[]};
const run={kind:'snapshot',version:'live.v1',run_id:'r1',phase:'awaiting_confirmation',runtime_state:null,goal:'Восстанови сервис',model_status:'ready',service_view:null,pending_confirmation:confirmation,stop_requested:false,terminal:null,cursor:0,server_time:time};
const session={kind:'session',provider:{kind:'simulator',model_name:null},version:'live.v1',session_id:'s1',server_time:time,reservation:null,current_run_id:'r1',model_status:'ready',preparation_error:null};
beforeEach(()=>{window.history.replaceState({garScreen:'home'},'','#home');localStorage.clear();});
afterEach(()=>vi.unstubAllGlobals());
function mockBackend({visitor=false,terminal=false,reservation=false,busyOnPrepare=false,reservationPhase='ready',absoluteExpiry=null as string|null}={}){
 let reserved=reservation;let admitted=false;
 const fetcher=vi.fn(async(path:string,options?:RequestInit)=>({ok:!(busyOnPrepare&&path==='/api/sessions'),json:async()=>{
  if(busyOnPrepare&&path==='/api/sessions')return {code:'LIVE_BUSY'};
  if(path.includes('/runs/success.json'))return success;
  if(path==='/api/status')return {kind:'status',version:'live.v1',availability:terminal?'available':'busy',model_status:'ready',server_time:time};
  if(path==='/api/sessions'){admitted=true;reserved=true;return {};}
  if(path==='/api/session/release'){reserved=false;return {};}
  if(path==='/api/session')return {...session,dialogue:reserved?{reservation_id:'res1',state:reservationPhase==='dialogue'?'thinking':reservationPhase,calls:0,reason:null,absolute_expires_at:absoluteExpiry,run_id:null,messages:[]}:null,current_run_id:visitor||reservation||admitted?null:'r1',reservation:reserved?{reservation_id:'res1',phase:reservationPhase,expires_at:reservationPhase==='preparing'?null:confirmation.expires_at,service_view:success.replay.events.find(e=>e.observation)!.observation}:null};
  if(path.includes('/events?'))return {kind:'events',version:'live.v1',run_id:'r1',events:[],next_cursor:0,has_more:false};
  if(path==='/api/runs/r1')return terminal?{...run,phase:'terminal',pending_confirmation:null,terminal:{origin:'platform',reason_code:'CONFIRMATION_EXPIRED',explanation:'Время истекло',runtime_outcome:null}}:run;
  throw new Error(`Unexpected ${options?.method} ${path}`);
 }}));
 vi.stubGlobal('fetch',fetcher);return fetcher;
}
const mutations=(fetcher:ReturnType<typeof mockBackend>)=>fetcher.mock.calls.filter(([,options])=>options?.method==='POST');
it('lets the owner view a demo and return with the same deadline, without any new command',async()=>{
 const fetcher=mockBackend();render(<App/>);
 const banner=await screen.findByLabelText('Ваш запуск');
 expect(banner).toHaveTextContent('На решение: 300 сек.');
 expect(screen.queryByText('Живой режим занят. Пока можно посмотреть демонстрационный пример.')).toBeNull();
 fireEvent.click(await screen.findByRole('button',{name:'Посмотреть пример'}));
 expect(screen.getByRole('complementary',{name:'Ваш запуск'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Вернуться к запуску'}));
 await screen.findByText('Ожидается решение оператора');
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
 await screen.findByText('Время истекло',{selector:'.outcome > p'});
 window.history.replaceState({garScreen:'demo'},'','#demo');fireEvent.popState(window);
 await screen.findByRole('button',{name:'Далее'});
 window.history.replaceState({garScreen:'live'},'','#live');fireEvent.popState(window);
 await screen.findByText('Время истекло',{selector:'.outcome > p'});
 expect(mutations(fetcher)).toEqual([]);
});
it.each(['preparing','ready','dialogue'])('preserves a %s reservation across home, demo and history without another admission',async(reservationPhase)=>{
 window.history.replaceState({garScreen:'live'},'','#live');
 const fetcher=mockBackend({reservation:true,reservationPhase});render(<App/>);
 if(reservationPhase==='dialogue')await screen.findByText('Агент отвечает');
 else await screen.findByRole('textbox',{name:'Запрос агенту'});
 window.history.replaceState({garScreen:'home'},'','#home');fireEvent.popState(window);
 await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(mutations(fetcher)).toHaveLength(0);
 expect(screen.getByRole('button',{name:'Вернуться к запуску'})).toBeVisible();
 expect(screen.queryByText('Живой режим занят. Пока можно посмотреть демонстрационный пример.')).toBeNull();
 if(reservationPhase==='preparing')expect(screen.getByLabelText('Ваш запуск')).toHaveTextContent('Подготовка модели');
 if(reservationPhase==='dialogue')expect(screen.getByLabelText('Ваш запуск')).toHaveTextContent('Агент обрабатывает запрос');
 if(reservationPhase==='ready')expect(screen.getByLabelText('Ваш запуск')).toHaveTextContent('На обращение: 300 сек.');
 fireEvent.click(screen.getByRole('button',{name:'Посмотреть пример'}));
 fireEvent.click(screen.getByRole('button',{name:'Вернуться к запуску'}));
 await screen.findByRole('region',{name:'Интерактивный диалог'});
 expect(mutations(fetcher)).toHaveLength(0);
});

it('starts again directly from the central chooser after a terminal run',async()=>{
 vi.stubGlobal('navigator',{locks:{request:async(_name:string,callback:()=>unknown)=>callback()}});
 const fetcher=mockBackend({terminal:true});render(<App/>);
 const button=await screen.findByRole('button',{name:'Начать заново'});
 expect(button.closest('.welcome')).not.toBeNull();
 expect(screen.getByRole('button',{name:'Посмотреть результат'}).closest('.welcome')).not.toBeNull();
 fireEvent.click(button);
 await screen.findByRole('textbox',{name:'Запрос агенту'});
 expect(mutations(fetcher)).toHaveLength(1);
 expect(JSON.parse(String(mutations(fetcher)[0][1]?.body)).command).toBe('prepare');
});

it('preserves result access when another session wins admission before restart',async()=>{
 vi.stubGlobal('navigator',{locks:{request:async(_name:string,callback:()=>unknown)=>callback()}});
 const fetcher=mockBackend({terminal:true,busyOnPrepare:true});render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:'Начать заново'}));
 await screen.findByText('Живой режим занят. Пока можно посмотреть демонстрационный пример.');
 expect(screen.getByRole('button',{name:'Посмотреть результат'})).toBeVisible();
 expect(screen.queryByRole('textbox',{name:'Запрос агенту'})).toBeNull();
 expect(mutations(fetcher)).toHaveLength(1);
});

it.each([[390,false],[390,true],[1280,false],[1280,true]])('keeps owner access beside navigation at width %s (terminal=%s)',async(width,terminal)=>{
 vi.stubGlobal('innerWidth',width);
 const fetcher=mockBackend({terminal});render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:'Посмотреть пример'}));
 const button=await screen.findByRole('button',{name:terminal?(width===390?'Результат живого запуска':'Результат запуска'):(width===390?/Вернуться к запуску · 5:00/:'Вернуться к запуску')});
 expect(button.closest('.demo-navigation')).not.toBeNull();
 expect(button.classList.contains('action')).toBe(true);
 expect(document.querySelector('.chat .owner-access')).toBeNull();
 fireEvent.click(button);
 await screen.findByRole('region',{name:'Интерактивный диалог'});
 expect(mutations(fetcher)).toHaveLength(0);
});

it('shows the earlier absolute dialogue deadline without renewing it on navigation',async()=>{
 const fetcher=mockBackend({reservation:true,absoluteExpiry:'2026-10-22T12:01:00Z'});render(<App/>);
 expect(await screen.findByLabelText('Ваш запуск')).toHaveTextContent('На обращение: 60 сек.');
 fireEvent.click(screen.getByRole('button',{name:'Вернуться к запуску'}));
 await screen.findByRole('textbox',{name:'Запрос агенту'});
 fireEvent.click(screen.getByRole('button',{name:'К началу'}));
 expect(await screen.findByLabelText('Ваш запуск')).toHaveTextContent('На обращение: 60 сек.');
 expect(mutations(fetcher)).toHaveLength(0);
});

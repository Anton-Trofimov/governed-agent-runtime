import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { LiveWorkspace } from './LiveWorkspace';
import { sessionSchema } from './live';

beforeEach(()=>{
  sessionStorage.clear();
  HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};
});
afterEach(()=>vi.unstubAllGlobals());
const service={observation_id:'obs-0',observed_at:'2026-10-25T00:00:00Z',stable_version_id:'2.4.1',candidate_version_id:'2.4.2',
  desired:6,healthy:6,candidate_count:2,stable_traffic_rps:615,total_rps:820,safe_rps_per_replica:150,
  conflicting_operation:false,rollout_state:'PAUSED',shift_id:null,recovery:{status:'UNKNOWN',shift_id:null}};
function session(){return sessionSchema.parse({kind:'session',version:'live.v1',session_id:'owner',server_time:new Date().toISOString(),
  current_run_id:null,model_status:'ready',provider:{kind:'simulator',model_name:null},preparation_error:null,
  reservation:{reservation_id:'reservation',phase:'ready',expires_at:new Date(Date.now()+300000).toISOString(),service_view:service},
  dialogue:{reservation_id:'reservation',state:'ready',messages:[],calls:0,reason:null,absolute_expires_at:new Date(Date.now()+600000).toISOString(),run_id:null}});}
const props={onExit:()=>{},renderState:()=>null,renderCompact:()=>null};
it('submits an initial question through dialogue and keeps answer plus input after reconnect',async()=>{
  const current=session();
  const fetcher=vi.fn(async(path:string,init?:RequestInit)=>{
    if(init?.method==='POST'){
      expect(path).toBe('/api/dialogue');
      const body=JSON.parse(String(init.body));expect(body.command).toBe('dialogue');expect(body.text).toBe('Что ты умеешь?');
      current.dialogue!.calls=1;
      current.dialogue!.messages=[{id:'u1',actor:'operator',text:body.text,occurred_at:current.server_time,outcome:null},
        {id:'a1',actor:'agent',text:'Могу объяснить состояние сервиса.',occurred_at:current.server_time,outcome:'answer'}];
    }
    return {ok:true,json:async()=>current};
  });
  vi.stubGlobal('fetch',fetcher);
  const view=render(<LiveWorkspace {...props}/>);
  fireEvent.change(await screen.findByRole('textbox',{name:'Запрос агенту'}),{target:{value:'Что ты умеешь?'}});
  fireEvent.click(screen.getByRole('button',{name:'Отправить'}));
  await screen.findByText('Могу объяснить состояние сервиса.');
  expect(screen.getByRole('textbox',{name:'Запрос агенту'})).toBeEnabled();
  expect(screen.queryByRole('button',{name:'Что ты умеешь?'})).toBeNull();
  expect(screen.getByRole('button',{name:'Почему сервис нестабилен?'})).toBeVisible();
  expect(screen.getByRole('textbox',{name:'Запрос агенту'})).toHaveValue('');
  expect(fetcher.mock.calls.filter(c=>c[1]?.method==='POST')).toHaveLength(1);
  view.unmount();render(<LiveWorkspace {...props}/>);
  await screen.findByText('Могу объяснить состояние сервиса.');
  expect(fetcher.mock.calls.filter(c=>c[1]?.method==='POST')).toHaveLength(1);
});
it('disables input during classification without presenting execution as started',async()=>{
  const current=session();current.dialogue!.state='thinking';current.reservation!.phase='dialogue';current.model_status='inference';
  current.dialogue!.messages=[{id:'u1',actor:'operator',text:'Почему нестабильно?',occurred_at:current.server_time,outcome:null}];
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>current})));
  render(<LiveWorkspace {...props}/>);
  expect(await screen.findByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  await waitFor(()=>expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toHaveValue('Агент обрабатывает сообщение. Выполнение ещё не начато.'));
  expect(screen.queryByRole('button',{name:'Подтвердить'})).toBeNull();
  expect(screen.getByRole('button',{name:'Завершить начальный диалог'})).toBeVisible();
});
it('retains terminal dialogue without a remediation result and permits a new admission',async()=>{
  const current=session();current.reservation=null;current.dialogue!.state='terminal';current.dialogue!.reason='DIALOGUE_LIMIT';
  current.preparation_error={code:'DIALOGUE_LIMIT',message:'Лимит начального диалога исчерпан.'};
  current.dialogue!.messages=[{id:'a1',actor:'agent',text:'Ответ сохранён.',occurred_at:current.server_time,outcome:'answer'}];
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>current})));
  render(<LiveWorkspace {...props}/>);
  await screen.findByText('Ответ сохранён.');
  expect(screen.queryByRole('button',{name:'Открыть итоговый отчёт'})).toBeNull();
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  expect(screen.getByRole('button',{name:/Начать/})).toBeEnabled();
});

it('warns before the fifth call and suggestions only populate editable text',async()=>{
  const current=session();current.dialogue!.calls=4;
  const fetcher=vi.fn(async()=>({ok:true,json:async()=>current}));vi.stubGlobal('fetch',fetcher);
  const view=render(<LiveWorkspace {...props}/>);
  expect(await screen.findByRole('dialog',{name:'Осталось одно обращение'})).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Понятно'}));
  expect(screen.queryByRole('dialog')).toBeNull();
  view.unmount();render(<LiveWorkspace {...props}/>);
  await screen.findByText('Обращения: 4/5');
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(screen.getByText('Обращения: 4/5')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Почему сервис нестабилен?'}));
  expect(screen.getByRole('textbox',{name:'Запрос агенту'})).toHaveValue('Почему сервис работает нестабильно?');
  fireEvent.click(screen.getByRole('button',{name:'Восстанови сервис'}));
  expect(screen.getByRole('textbox',{name:'Запрос агенту'})).toHaveValue('Восстанови работу сервиса');
  expect(fetcher.mock.calls.filter(c=>(c as unknown as [string,RequestInit])[1]?.method==='POST')).toHaveLength(0);
});

it('closes the notice when the server expires the dialogue without sending a command',async()=>{
  const current=session();current.dialogue!.calls=4;
  const fetcher=vi.fn(async()=>({ok:true,json:async()=>current}));
  vi.stubGlobal('fetch',fetcher);
  render(<LiveWorkspace {...props}/>);
  await screen.findByRole('dialog',{name:'Осталось одно обращение'});
  current.dialogue!.state='terminal';current.dialogue!.reason='DIALOGUE_EXPIRED';current.reservation=null;
  await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull(),{timeout:4000});
  expect(screen.getByRole('textbox',{name:'Состояние диалога'})).toBeDisabled();
  expect(fetcher.mock.calls.filter(c=>(c as unknown as [string,RequestInit])[1]?.method==='POST')).toHaveLength(0);
});

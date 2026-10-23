import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { App } from './App';
import { parseRun, readSelection, saveSelection, loadRun, type Run } from './data';
import success from '../public/runs/success.json';
import stop from '../public/runs/stop.json';
beforeEach(()=>{HTMLDialogElement.prototype.showModal=function(){this.open=true;}; HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};vi.restoreAllMocks();localStorage.clear();window.history.replaceState(null,'','/');vi.unstubAllGlobals();});
const loader=async(id:string)=>parseRun(id==='success'?success:stop,id);
async function start(){fireEvent.click(await screen.findByRole('button',{name:'Посмотреть пример'}));}
function finish(){fireEvent.click(screen.getByRole('button',{name:'К результату'}));}
it('replays observations without leaking final state and resets to the initial observation',async()=>{
 render(<App loader={loader}/>);
 await start();
 const state=screen.getByRole('region',{name:'Состояние системы'});
 expect(within(state).getByText('615')).toBeVisible();
 expect(screen.queryByRole('heading',{name:'Откат завершён'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Подтвердить'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Далее'}));
 expect(screen.getByText(success.replay.events[1].summary)).toBeVisible();
 expect(screen.getByText(success.replay.events[1].text)).toBeVisible();
 finish();
 expect(screen.getByRole('heading',{name:'Откат завершён'})).toBeVisible();
 expect(within(state).queryByText('615')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'К началу'}));
 expect(within(screen.getByRole('region',{name:'Состояние системы'})).getByText('615')).toBeVisible();
 expect(screen.queryByRole('heading',{name:'Откат завершён'})).not.toBeInTheDocument();
}, 15000); // Full replay/reset traverses the complete recorded DOM in jsdom.
it('switches runs without old state under the new selection',async()=>{
 let resolve:(r:Run)=>void=()=>{};
 const delayed=(id:string)=>id==='success'?loader(id):new Promise<Run>(r=>{resolve=r;});
 render(<App loader={delayed}/>);await start();finish();
 fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:'stop'}});
 expect(screen.queryByRole('heading',{name:'Откат завершён'})).not.toBeInTheDocument();
 expect(screen.getByText('Загрузка сохранённых данных…')).toBeVisible();
 resolve(parseRun(stop,'stop'));await screen.findByRole('button',{name:'К результату'});finish();
 expect(screen.getByRole('heading',{name:'Выполнение остановлено'})).toBeVisible();
 expect(screen.getByText('Проверка восстановления завершилась с FAIL. Восстановление сервиса не подтверждено.')).toBeVisible();
 expect(readSelection()).toBe('stop');
});
it('shows an error when data cannot load',async()=>{
 render(<App loader={async()=>{throw Error('missing');}}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Состояние системы не установлено');
});
it('suppresses reassurance for an unknown write outcome',async()=>{
 const value=structuredClone(stop);value.view.unknown_write_effect=true;
 render(<App loader={async()=>parseRun(value,'stop')}/>);await start();finish();
 expect(screen.getByRole('heading',{name:'Исход изменения неизвестен'})).toBeVisible();
 expect(screen.getByText(/Последние данные до изменения с неизвестным исходом/)).toBeVisible();
});
it('works without browser storage',async()=>{
 vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw Error('disabled');});
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('disabled');});
 expect(readSelection()).toBe('success');expect(()=>saveSelection('stop')).not.toThrow();
 render(<App loader={loader}/>);await start();finish();
 expect(screen.getByRole('heading',{name:'Откат завершён'})).toBeVisible();
});
it('falls back from obsolete selection',()=>{
 localStorage.setItem('governed-agent.viewer.v1.selected-run','obsolete');expect(readSelection()).toBe('success');
});
it('ignores a stale response',async()=>{
 let resolve:(r:Run)=>void=()=>{};
 const delayed=(id:string)=>id==='success'?loader(id):new Promise<Run>(r=>{resolve=r;});
 render(<App loader={delayed}/>);await start();
 fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:'stop'}});
 fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:'success'}});
 await screen.findByRole('button',{name:'К результату'});finish();resolve(parseRun(stop,'stop'));
 await waitFor(()=>expect(screen.getByRole('heading',{name:'Откат завершён'})).toBeVisible());
});
it('rejects missing, malformed and mismatched network data',async()=>{
 const fetcher=vi.spyOn(globalThis,'fetch');
 fetcher.mockResolvedValue({ok:false} as Response);await expect(loadRun('success')).rejects.toThrow();
 fetcher.mockResolvedValue({ok:true,json:async()=>stop} as Response);await expect(loadRun('success')).rejects.toThrow();
 fetcher.mockResolvedValue({ok:true,json:async()=>({})} as Response);await expect(loadRun('success')).rejects.toThrow();
});
it('gates mode controls and keeps versions always visible',async()=>{
 render(<App loader={loader}/>);await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(screen.queryByLabelText('Демонстрационный пример')).not.toBeInTheDocument();
 expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
 expect(screen.getByText('Версии и реплики').closest('details')).toBeNull();
 expect(screen.getByText('Условия безопасной работы').closest('details')!.open).toBe(true);
 expect(screen.getByRole('button',{name:'Начать живой сценарий'})).toBeDisabled();
 await start();expect(screen.getByLabelText('Демонстрационный пример')).toBeVisible();finish();
 fireEvent.click(screen.getByRole('button',{name:'Открыть итоговый отчёт'}));
 expect(screen.getByRole('dialog',{name:'Итоговый отчёт'})).toBeVisible();
 expect(document.querySelector('.report pre')!.textContent).toBe(success.report);
});
it('keeps mobile versions visible and safety conditions initially closed',async()=>{
 const original=window.matchMedia;
 window.matchMedia=vi.fn().mockReturnValue({matches:true});
 try {
  render(<App loader={loader}/>);await screen.findByRole('button',{name:'Посмотреть пример'});
  expect(screen.getByText('Версии и реплики').closest('details')).toBeNull();
  expect(screen.getByText('Условия безопасной работы').closest('details')!.open).toBe(false);
  expect(screen.getByText('Общий трафик')).toBeVisible();
 } finally { window.matchMedia=original; }
});
it('emphasizes changes only after observed updates and clears emphasis',async()=>{
 render(<App loader={loader}/>);await start();
 expect(document.querySelector('.value-changed')).toBeNull();
 const index=success.replay.events.findIndex(e=>e.kind==='observation_applied');
 for(let i=0;i<index;i++)fireEvent.click(screen.getByRole('button',{name:'Далее'}));
 expect(document.querySelector('.value-changed')).not.toBeNull();
 await waitFor(()=>expect(document.querySelector('.value-changed')).toBeNull(),{timeout:2500});
});

it('shows recorded confirmations as disabled choices, never actionable consent',async()=>{
 render(<App loader={loader}/>);await start();finish();
 const confirms=screen.getAllByRole('button',{name:'Подтвердить'});
 expect(confirms.length).toBe(3);
 confirms.forEach(button=>{expect(button).toBeDisabled();expect(button).toHaveAttribute('aria-pressed','true');});
 screen.getAllByRole('button',{name:'Отклонить'}).forEach(button=>expect(button).toBeDisabled());
 expect(screen.getByText('Запрос для демонстрации')).toBeVisible();
 expect(screen.getByText('Восстанови работу сервиса')).toBeVisible();
});
it('opens explanatory dialog only on demand and restores trigger focus',async()=>{
 // jsdom does not implement native dialog methods; test our open/close wiring.
 HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};
 render(<App loader={loader}/>);await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 const trigger=screen.getByRole('button',{name:'ⓘ Как это работает'});
 fireEvent.click(trigger);
 const dialog=screen.getByRole('dialog');
 expect(dialog).toHaveTextContent('Подтверждение оператора тоже не отменяет проверки платформы');
 expect(dialog).toHaveTextContent('инференс LLM осуществляется на реальной AI-инфраструктуре');
 fireEvent.click(within(dialog).getByRole('button',{name:'Закрыть'}));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(trigger).toHaveFocus();
});
it('highlights the compact state and advances without scrolling the page',async()=>{
 const scroll=vi.fn();
 const original=HTMLElement.prototype.scrollIntoView;
 HTMLElement.prototype.scrollIntoView=scroll;
 try {
  render(<App loader={loader}/>);await start();
  expect(scroll).toHaveBeenCalledTimes(1);
  scroll.mockClear();finish();
  expect(document.querySelector('.compact-state .value-changed')).not.toBeNull();
  expect(scroll).not.toHaveBeenCalled();
 } finally {HTMLElement.prototype.scrollIntoView=original;}
});

it('keeps the event breakdown in replay only and derives counts for each example',async()=>{
 render(<App loader={loader}/>);
 await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(screen.queryByLabelText('Состав событий')).not.toBeInTheDocument();
 await start();
 const details=screen.getByLabelText('Состав событий').closest('details')!;
 expect(details).not.toHaveAttribute('open');
 expect(details).toHaveTextContent('Состав событий: 33');
 expect(details).toHaveTextContent('Остальные: 11');
 expect(details).toHaveTextContent('3 явных подтверждения');
 expect(details).toHaveTextContent('Вызовы инструментов: 6');
 details.open=true;
 fireEvent.click(within(details).getByRole('button',{name:'Закрыть состав событий'}));
 expect(details).not.toHaveAttribute('open');
 expect(screen.getByLabelText('Состав событий')).toHaveFocus();
 expect(document.querySelector('.about-dialog')).not.toHaveTextContent('Состав событий');
 fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:'stop'}});
 await waitFor(()=>expect(screen.getByLabelText('Состав событий').closest('details')).toHaveTextContent('Состав событий: 26'));
 expect(screen.getByLabelText('Состав событий').closest('details')).toHaveTextContent('Остальные: 8');
 expect(screen.getByLabelText('Состав событий').closest('details')).toHaveTextContent('2 явных подтверждения');
});

it('uses the logo as home navigation and keeps translation guidance out of welcome',async()=>{
 render(<App loader={loader}/>);
 await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(screen.queryByText(/Ответ агента записан на английском/)).not.toBeInTheDocument();
 await start();
 fireEvent.click(screen.getByRole('link',{name:/Governed Agent/}));
 await screen.findByRole('button',{name:'Посмотреть пример'});
 expect(screen.queryByRole('button',{name:'Далее'})).not.toBeInTheDocument();
});

it.each(['success','stop'])('links %s proposal and checks without scrolling the page',async(id)=>{
 const scroll=vi.fn();const original=HTMLElement.prototype.scrollIntoView;
 HTMLElement.prototype.scrollIntoView=scroll;
 try{
  render(<App loader={loader}/>);await start();
  fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:id}});
  await screen.findByRole('button',{name:'К результату'});finish();scroll.mockClear();
  const proposal=document.querySelector<HTMLElement>('.messages [data-event-source="event-60"]')!;
  (proposal.querySelector('details') as HTMLDetailsElement).open=true;
  fireEvent.click(within(proposal).getAllByRole('button',{name:'Показать в журнале'})[0]);
  const check=document.querySelector<HTMLElement>('.journal [data-event-source="event-61"]')!;
  expect(check).toHaveAttribute('data-highlight','true');
  expect(check.querySelector('details')).toHaveAttribute('open');
  expect(check).toHaveFocus();
  fireEvent.click(within(check).getByRole('button',{name:'Показать в чате'}));
  expect(proposal).toHaveAttribute('data-highlight','true');
  expect(proposal).toHaveFocus();
  expect(scroll).not.toHaveBeenCalled();
 }finally{HTMLElement.prototype.scrollIntoView=original;}
});
it('does not expose future checks before playback reveals them',async()=>{
 render(<App loader={loader}/>);await start();
 fireEvent.click(screen.getByRole('button',{name:'Далее'}));
 const proposal=document.querySelector('.messages [data-event-source="event-4"]')!;
 expect(proposal).not.toHaveTextContent('event-5');
});

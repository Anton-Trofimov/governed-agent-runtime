import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { App } from './App';
import success from '../public/runs/success.json';
import stop from '../public/runs/stop.json';
beforeEach(()=>{
  localStorage.clear(); window.history.replaceState({garScreen:'live'},'', '/#live');
  HTMLDialogElement.prototype.showModal=function(){this.open=true;};
});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
it('defaults to autonomous viewing despite saved live history; never calls the live API',async()=>{
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
    const path=String(input);
    if(path.includes('runs/success.json'))return {ok:true,json:async()=>success} as Response;
    if(path.includes('runs/stop.json'))return {ok:true,json:async()=>stop} as Response;
    throw Error('Unexpected live request');
  });
  render(<App/>);
  await screen.findByRole('button',{name:'Посмотреть пример'});
  expect(fetcher.mock.calls.every(([url])=>String(url).includes('runs/'))).toBe(true);
  expect(screen.queryByRole('button',{name:'Начать живой сценарий'})).toBeNull();
  expect(screen.getByText('Живой режим сейчас недоступен. Вы можете посмотреть сохранённый пример.')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Посмотреть пример'}));
  fireEvent.click(screen.getByRole('button',{name:'К результату'}));
  fireEvent.click(screen.getByRole('button',{name:'Открыть итоговый отчёт'}));
  expect(screen.getByRole('dialog',{name:'Итоговый отчёт'})).toBeVisible();
  fireEvent.change(screen.getByLabelText('Демонстрационный пример'),{target:{value:'stop'}});
  await screen.findByText(/Проверка восстановления не пройдена/);
  fireEvent.click(screen.getByRole('button',{name:'К результату'}));
  expect(screen.getByRole('heading',{name:'Выполнение остановлено'})).toBeVisible();
  vi.useFakeTimers();
  window.history.replaceState({garScreen:'live'},'', '/#live');
  act(()=>{window.dispatchEvent(new PopStateEvent('popstate'));});
  await act(async()=>{await vi.advanceTimersByTimeAsync(10000);});
  expect(window.location.hash).toBe('#home');
  expect(fetcher.mock.calls.every(([url])=>String(url).includes('runs/'))).toBe(true);
});

import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ConfiguredApp } from './ConfiguredApp';
import { loadMode } from './config';
import success from '../public/runs/success.json';
beforeEach(()=>{window.history.replaceState(null,'','/');});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
it.each([null, {}, {mode:'live'}, {mode:''}, {mode:'live-enabled',extra:true}, ['live-enabled'], {mode:'recorded-only'}])('fails closed for %j',async value=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:async()=>value} as Response);
  expect(await loadMode()).toBe('recorded-only');
});
it.each(['network','missing','malformed'])('fails closed on %s configuration',async failure=>{
  vi.spyOn(globalThis,'fetch').mockImplementation(async()=>{
    if(failure==='network')throw Error('network');
    return new Response('{broken', {status:failure==='missing'?404:200});
  });
  expect(await loadMode()).toBe('recorded-only');
});
it('requests only the static configuration without credentials or cached redirects',async()=>{
  const fetcher=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:async()=>({mode:'live-enabled'})} as Response);
  expect(await loadMode()).toBe('live-enabled');
  expect(fetcher).toHaveBeenCalledWith('/app-config.json',expect.objectContaining({credentials:'omit',cache:'no-store',redirect:'error',signal:expect.any(AbortSignal)}));
});
it('bounds response decoding and ignores late live-enabled configuration',async()=>{
  vi.useFakeTimers();
  let finish!:(value:unknown)=>void;
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:()=>new Promise(resolve=>{finish=resolve;})} as Response);
  const result=loadMode();
  await vi.advanceTimersByTimeAsync(3000);
  expect(await result).toBe('recorded-only');
  finish({mode:'live-enabled'});
  expect(await result).toBe('recorded-only');
});
it('entry waits for configuration, then uses recorded assets without any API or live controls',async()=>{
  let finish!:(value:Response)=>void;
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async path=>{
    if(String(path).endsWith('app-config.json'))return new Promise(resolve=>{finish=resolve;});
    if(String(path).endsWith('runs/success.json'))return {ok:true,json:async()=>success} as Response;
    throw Error('Unexpected request');
  });
  const first=render(<ConfiguredApp/>);
  expect(screen.getByText('Загрузка интерфейса…')).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(1);
  await act(async()=>{finish({ok:true,json:async()=>({mode:'recorded-only'})} as Response);});
  fireEvent.click(await screen.findByRole('button',{name:'Посмотреть пример'}));
  expect(screen.queryByRole('button',{name:'Начать живой сценарий'})).toBeNull();
  expect(fetcher.mock.calls.every(([path])=>!String(path).includes('/api/'))).toBe(true);
  first.unmount();
  render(<ConfiguredApp/>);
  await act(async()=>{finish({ok:false} as Response);});
  await screen.findByRole('button',{name:'К результату'});
  expect(fetcher.mock.calls.every(([path])=>!String(path).includes('/api/'))).toBe(true);
});
it('explicit live-enabled configuration initializes the existing status transport',async()=>{
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async path=>{
    if(String(path).endsWith('app-config.json'))return {ok:true,json:async()=>({mode:'live-enabled'})} as Response;
    if(String(path).endsWith('runs/success.json'))return {ok:true,json:async()=>success} as Response;
    throw Error('No backend in this test');
  });
  render(<ConfiguredApp/>);
  await screen.findByRole('button',{name:'Начать живой сценарий'});
  expect(fetcher.mock.calls.some(([path])=>path==='/api/status')).toBe(true);
});
it('recorded asset failure and unavailable storage never trigger live fallback',async()=>{
  vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw Error('denied');});
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('denied');});
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async path=>({ok:true,json:async()=>String(path).endsWith('app-config.json')?{mode:'recorded-only'}:{}} as Response));
  render(<ConfiguredApp/>);
  await screen.findByRole('heading',{name:'Данные запуска недоступны'});
  fireEvent.click(screen.getByRole('button',{name:'Повторить загрузку'}));
  await screen.findByRole('heading',{name:'Данные запуска недоступны'});
  expect(fetcher.mock.calls.every(([path])=>!String(path).includes('/api/'))).toBe(true);
});

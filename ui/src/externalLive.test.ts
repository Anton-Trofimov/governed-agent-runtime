import { afterEach, expect, it, vi } from 'vitest';
import { loadMode } from './config';
import { observeAvailability } from './externalLive';

afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
it('recognizes only the explicit HTTPS external-entry profile', async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({mode:'external-entry',origin:'https://demo.example'})));
  expect(await loadMode()).toBe('external-entry');
});

it.each(['http://demo.example','https://demo.example/path','https://user:pass@demo.example','https://demo.example/?token=x'])('rejects unsafe entry %s',async origin=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({mode:'external-entry',origin})));
  expect(await loadMode()).toBe('recorded-only');
});

const reply=(availability='available')=>new Response(JSON.stringify({availability,provider:'simulator'}));
it('keeps confirmed availability over two failures, backs off, and requires two recovery replies',async()=>{
  vi.useFakeTimers();
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async()=>reply());
  const publish=vi.fn();
  const stop=observeAvailability('https://demo.example',publish);
  await vi.advanceTimersByTimeAsync(0);
  expect(publish).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(15000);
  expect(publish.mock.calls).toEqual([['available']]);
  fetcher.mockRejectedValue(Error('network'));
  await vi.advanceTimersByTimeAsync(30000);
  expect(publish.mock.calls).toEqual([['available']]);
  await vi.advanceTimersByTimeAsync(15000);
  expect(publish.mock.calls).toEqual([['available'],['unavailable']]);
  await vi.advanceTimersByTimeAsync(15000); // fourth failure -> 30 seconds
  const count=fetcher.mock.calls.length;
  await vi.advanceTimersByTimeAsync(29999);
  expect(fetcher).toHaveBeenCalledTimes(count);
  fetcher.mockImplementation(async()=>reply());
  await vi.advanceTimersByTimeAsync(1);
  expect(publish).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(15000);
  expect(publish.mock.calls).toEqual([['available'],['unavailable'],['available']]);
  expect(fetcher.mock.calls.every(([url])=>url==='https://demo.example/public/status')).toBe(true);
  expect(fetcher).toHaveBeenCalledWith(expect.any(String),expect.objectContaining({credentials:'omit',redirect:'error',cache:'no-store'}));
  stop();
});

it('bounds a stalled body, ignores late responses and never overlaps probes',async()=>{
  vi.useFakeTimers();
  let finish!:(value:unknown)=>void;
  const fetcher=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:()=>new Promise(resolve=>{finish=resolve;})} as Response);
  const publish=vi.fn();
  const stop=observeAvailability('https://demo.example',publish);
  await vi.advanceTimersByTimeAsync(4000);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect((fetcher.mock.calls[0][1]!.signal as AbortSignal).aborted).toBe(true);
  finish({availability:'available',provider:'simulator'});
  await vi.advanceTimersByTimeAsync(14999);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(publish).not.toHaveBeenCalled();
  stop();
  await vi.advanceTimersByTimeAsync(60000);
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it('treats busy as reachable, explicit pause as unavailable, and suspends hidden tabs',async()=>{
  vi.useFakeTimers();
  let hidden=false;
  vi.spyOn(document,'hidden','get').mockImplementation(()=>hidden);
  const fetcher=vi.spyOn(globalThis,'fetch').mockImplementation(async()=>reply('busy'));
  const publish=vi.fn();
  const stop=observeAvailability('https://demo.example',publish);
  await vi.advanceTimersByTimeAsync(15000);
  expect(publish).toHaveBeenLastCalledWith('busy');
  hidden=true;document.dispatchEvent(new Event('visibilitychange'));
  const count=fetcher.mock.calls.length;
  await vi.advanceTimersByTimeAsync(120000);
  expect(fetcher).toHaveBeenCalledTimes(count);
  fetcher.mockImplementation(async()=>reply('unavailable'));
  hidden=false;document.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(0);
  expect(publish).toHaveBeenLastCalledWith('unavailable');
  stop();
});

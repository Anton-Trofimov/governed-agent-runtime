export type Availability = 'available' | 'busy' | 'unavailable';

// The observer never starts sessions or changes application navigation.
export function observeAvailability(origin: string, publish: (state: Availability) => void) {
  let stopped = false, running = false, failures = 0, successes = 0;
  let state: Availability = 'unavailable';
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  function update(next: Availability) { if (next !== state) { state = next; publish(next); } }
  async function probe() {
    if (stopped || running || document.hidden) return;
    running = true;
    controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
      const read = async () => {
        const response = await fetch(`${origin}/public/status`, {
          credentials:'omit',cache:'no-store',redirect:'error',signal:controller!.signal,
        });
        if (!response.ok) throw Error('status');
        const value = await response.json();
        if (!value || Object.keys(value).length !== 2 || value.provider !== 'simulator'
            || !['available','busy','unavailable'].includes(value.availability)) throw Error('shape');
        return value.availability as Availability;
      };
      const next = await Promise.race([read(), new Promise<never>((_,reject)=>{
        timeout=setTimeout(()=>{controller?.abort();reject(Error('timeout'));},4000);
      })]);
      if (stopped) return;
      failures=0;
      if (next === 'unavailable') { successes=0; update(next); }
      else { successes++; if (state !== 'unavailable' || successes >= 2) update(next); }
    } catch {
      if (stopped) return;
      successes=0; failures++;
      if (failures >= 3) update('unavailable');
    } finally {
      clearTimeout(timeout); running=false;
      if (!stopped && !document.hidden) timer=setTimeout(probe,Math.min(60000,15000*2**Math.max(0,failures-1)));
    }
  }
  function visibility() { clearTimeout(timer); if (!document.hidden) void probe(); }
  document.addEventListener('visibilitychange',visibility);
  void probe();
  return () => { stopped=true; clearTimeout(timer); controller?.abort(); document.removeEventListener('visibilitychange',visibility); };
}

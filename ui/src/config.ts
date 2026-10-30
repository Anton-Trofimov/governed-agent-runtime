export type AppMode = 'recorded-only' | 'live-enabled';

// Presentation only. Backend admission and authorization remain independent.
export async function loadMode(): Promise<AppMode> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<AppMode>(resolve => {
    timer = setTimeout(() => { controller.abort(); resolve('recorded-only'); }, 3000);
  });
  const read = async (): Promise<AppMode> => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}app-config.json`, {
        credentials: 'omit', cache: 'no-store', redirect: 'error', signal: controller.signal,
      });
      if (!response.ok) return 'recorded-only';
      const value: unknown = await response.json();
      if (value && typeof value === 'object' && !Array.isArray(value)
          && Object.keys(value).length === 1 && 'mode' in value
          && value.mode === 'live-enabled') return 'live-enabled';
    } catch { /* Static viewing is available even when configuration is not. */ }
    return 'recorded-only';
  };
  try { return await Promise.race([read(), timeout]); }
  finally { clearTimeout(timer!); }
}

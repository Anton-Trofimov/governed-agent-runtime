export type AppMode = 'recorded-only' | 'live-enabled' | 'external-entry';
export type AppConfig = {mode: AppMode; origin?: string};

export function validOrigin(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  try { const url = new URL(value); return url.protocol === 'https:' && url.origin === value && !url.username && !url.password; }
  catch { return false; }
}

// Presentation only. Backend admission and authorization remain independent.
export async function loadConfig(): Promise<AppConfig> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<AppConfig>(resolve => {
    timer = setTimeout(() => { controller.abort(); resolve({mode:'recorded-only'}); }, 3000);
  });
  const read = async (): Promise<AppConfig> => {
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}app-config.json`, {
        credentials: 'omit', cache: 'no-store', redirect: 'error', signal: controller.signal,
      });
      if (!response.ok) return {mode:'recorded-only'};
      const value: unknown = await response.json();
      if (value && typeof value === 'object' && !Array.isArray(value)
          && Object.keys(value).length === 1 && 'mode' in value
          && value.mode === 'live-enabled') return {mode:'live-enabled'};
      if (value && typeof value === 'object' && !Array.isArray(value)
          && Object.keys(value).length === 2 && 'mode' in value && value.mode === 'external-entry'
          && 'origin' in value && validOrigin(value.origin)) return {mode:'external-entry',origin:value.origin};
    } catch { /* Static viewing is available even when configuration is not. */ }
    return {mode:'recorded-only'};
  };
  try { return await Promise.race([read(), timeout]); }
  finally { clearTimeout(timer!); }
}

export async function loadMode(): Promise<AppMode> { return (await loadConfig()).mode; }

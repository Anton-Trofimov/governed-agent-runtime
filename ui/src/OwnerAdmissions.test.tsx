import { expect, it, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OwnerAdmissions } from './OwnerAdmissions';

afterEach(()=>vi.unstubAllGlobals());
it('changes only public admissions without starting a session or run',async()=>{
  const change=vi.fn();
  const fetcher=vi.fn(async()=>({ok:true,json:async()=>({public_admissions_enabled:true})}));
  vi.stubGlobal('fetch',fetcher);
  render(<OwnerAdmissions enabled={false} connected onChange={change}/>);
  fireEvent.click(screen.getByRole('button',{name:'Разрешить публичные запуски'}));
  await waitFor(()=>expect(change).toHaveBeenCalledWith(true));
  expect(fetcher).toHaveBeenCalledTimes(1);
  const [path,options]=fetcher.mock.calls[0] as unknown as [string,RequestInit];
  expect(path).toBe('/api/admin/admissions');
  expect(JSON.parse(String(options.body))).toEqual({command:'set_public_admissions',command_id:expect.any(String),enabled:true});
});
it('disables the owner switch when connection is unavailable',()=>{
  render(<OwnerAdmissions enabled connected={false} onChange={()=>{}}/>);
  expect(screen.getByRole('button')).toBeDisabled();
});

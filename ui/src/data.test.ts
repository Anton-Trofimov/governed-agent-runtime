import { describe, it, expect } from 'vitest';
import success from '../public/runs/success.json';
import stop from '../public/runs/stop.json';
import { parseRun } from './data';
describe('saved-run boundary', () => {
  it('accepts the generated views', () => {
    expect(parseRun(success, 'success').view.rollback_completed).toBe(true);
    expect(parseRun(stop, 'stop').view.rollback_completed).toBe(false);
  });
  it.each([null, {}, {...success, view: {...success.view, view_version: '99'}},
    {...success, view: {...success.view, observation: {value: {healthy: '8'}}}},
    {...success, view: {...success.view, unknown_write_effect: true}}
  ])('rejects malformed/unsupported or contradictory data', (value) => {
    expect(() => parseRun(value, 'success')).toThrow();
  });
  it('rejects cross-run data instead of mixing panels', () => {
    expect(() => parseRun(stop, 'success')).toThrow();
  });
});

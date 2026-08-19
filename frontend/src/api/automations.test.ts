import { beforeEach, describe, expect, it, vi } from 'vitest';
import { preflightAutomation, resolveAutomationAccounts, runAutomation } from './automations';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const response = (data: unknown) => ({
  ok: true,
  status: 200,
  headers: new Headers({ 'content-type': 'application/json' }),
  json: () => Promise.resolve(data),
});

describe('Automations API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests a read-only preflight without mutation data', async () => {
    mockFetch.mockResolvedValueOnce(response({
      automation_id: 'test-automation', status: 'ready', checks: [], requirements: [], supports_profile_execution: true, mutations_applied: false,
    }));

    await preflightAutomation('test-automation');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/automations/test-automation/preflight',
      expect.objectContaining({ method: 'POST', body: '{}' }),
    );
  });

  it('reads account resolution metadata without requesting secret material', async () => {
    mockFetch.mockResolvedValueOnce(response({
      automation_id: 'news', accounts: [], credential_mappings: [], missing_requirements: [], ready: true,
    }));

    const result = await resolveAutomationAccounts('news');

    expect(result.ready).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/automations/news/accounts',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('runs an enabled automation with only an optional profile reference', async () => {
    mockFetch.mockResolvedValueOnce(response({
      success: true, automation_id: 'test-automation', execution_id: 'execution-1', status: 'running', profile_id: 'profile-1',
    }));

    await runAutomation('test-automation', 'profile-1');

    const options = mockFetch.mock.calls[0][1];
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/api/v1/automations/test-automation/run');
    expect(options).toEqual(expect.objectContaining({ method: 'POST', body: JSON.stringify({ profile_id: 'profile-1' }) }));
    expect(options.body).not.toContain('credential');
    expect(options.body).not.toContain('token');
    expect(options.body).not.toContain('secret');
  });
});

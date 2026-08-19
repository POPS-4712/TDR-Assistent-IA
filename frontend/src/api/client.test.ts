import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, setAuthToken } from './client';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Helper to create mock response
const createMockResponse = (data: unknown, options: { ok: boolean; status: number } = { ok: true, status: 200 }) => ({
  ok: options.ok,
  status: options.status,
  headers: new Headers({ 'content-type': 'application/json' }),
  json: () => Promise.resolve(data),
});

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
  });

  it('should make GET request', async () => {
    const mockResponse = { data: { test: 'value' } };
    mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

    const result = await api.get('/test');
    expect(result.data).toEqual(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/test',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('should make POST request', async () => {
    const mockResponse = { data: { created: true } };
    mockFetch.mockResolvedValueOnce(createMockResponse(mockResponse));

    const result = await api.post('/test', { name: 'test' });
    expect(result.data).toEqual(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/test',
      expect.objectContaining({ 
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      })
    );
  });

  it('should handle HTTP errors', async () => {
    mockFetch.mockResolvedValueOnce(createMockResponse({ detail: 'Not found' }, { ok: false, status: 404 }));

    await expect(api.get('/notfound')).rejects.toThrow('Not Found');
  });

  it('should handle network errors', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await expect(api.get('/test')).rejects.toThrow('Network error');
  });

  it('should include Authorization header when token is set', async () => {
    setAuthToken('test-token');
    
    mockFetch.mockResolvedValueOnce(createMockResponse({ data: {} }));

    await api.get('/test');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
        }),
      })
    );
  });
});

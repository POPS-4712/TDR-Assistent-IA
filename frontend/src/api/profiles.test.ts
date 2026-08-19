import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('./client', () => ({
  api: { get: mocks.get, post: mocks.post, put: mocks.put, delete: mocks.remove },
}));

import * as profilesApi from './profiles';

const profile = {
  id: 'profile-1',
  name: 'Technology',
  description: '',
  profession: { name: 'Engineer', sector: 'Technology', level: '' },
  interests: [], skills: [], companies: [], locations: [], languages: [], topics: [], excluded_topics: [], goals: [],
  preferences: { news_frequency: 'daily', relevance_level: 'high', sources: [], notifications_enabled: true, additional_settings: {} },
  is_active: true, is_enabled: true, created_at: '2026-08-18T00:00:00Z', updated_at: '2026-08-18T00:00:00Z',
};

describe('profiles API adapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists profiles through the local backend boundary', async () => {
    mocks.get.mockResolvedValue({ data: { profiles: [profile], total: 1 } });

    const response = await profilesApi.listProfiles();

    expect(mocks.get).toHaveBeenCalledWith('/profiles');
    expect(response.profiles[0].name).toBe('Technology');
  });

  it('activates a profile without submitting credentials', async () => {
    mocks.post.mockResolvedValue({ data: profile });

    await profilesApi.activateProfile('profile-1');

    expect(mocks.post).toHaveBeenCalledWith('/profiles/profile-1/activate', {});
  });

  it('sends an export bundle unchanged when restoring a profile', async () => {
    const bundle = { schema_version: '1.0', exported_at: '2026-08-18T00:00:00Z', profile: { ...profile, automations: [] } };
    mocks.post.mockResolvedValue({ data: profile });

    await profilesApi.importProfile(bundle);

    expect(mocks.post).toHaveBeenCalledWith('/profiles/import', { ...bundle, activate: false });
  });
});

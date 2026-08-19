import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ApiError } from '../api/client';
import * as profilesApi from '../api/profiles';
import { preflightAllAutomations } from '../api/automations';
import type { Profile, ProfileContext as ProfileAutomationContext, ProfileInput, ProfileUpdate } from '../types/profiles';

interface ProfileState {
  profiles: Profile[];
  activeProfile: Profile | null;
  isLoading: boolean;
  error: ApiError | null;
  refreshProfiles: () => Promise<void>;
  activateProfile: (profileId: string) => Promise<Profile>;
  createProfile: (payload: ProfileInput) => Promise<Profile>;
  updateProfile: (profileId: string, payload: ProfileUpdate) => Promise<Profile>;
  deleteProfile: (profileId: string) => Promise<void>;
  duplicateProfile: (profileId: string) => Promise<Profile>;
  getProfileContext: (profileId: string) => Promise<ProfileAutomationContext>;
  clearError: () => void;
}

const ProfileContext = createContext<ProfileState | undefined>(undefined);

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : ApiError.networkError(String(error));
}

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const rerunPreflight = useCallback(async () => {
    try {
      await preflightAllAutomations();
    } catch {
      // Profile changes remain valid even if a separate read-only status refresh is unavailable.
    }
  }, []);

  const refreshProfiles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await profilesApi.listProfiles();
      setProfiles(response.profiles);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshProfiles();
  }, [refreshProfiles]);

  const activeProfile = useMemo(
    () => profiles.find((profile) => profile.is_active) ?? null,
    [profiles],
  );

  const activateProfile = useCallback(async (profileId: string) => {
    try {
      const active = await profilesApi.activateProfile(profileId);
      setProfiles((current) => current.map((profile) => ({
        ...profile,
        is_active: profile.id === active.id,
      })));
      await rerunPreflight();
      return active;
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, [rerunPreflight]);

  const createProfile = useCallback(async (payload: ProfileInput) => {
    try {
      const created = await profilesApi.createProfile(payload);
      await Promise.all([refreshProfiles(), rerunPreflight()]);
      return created;
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, [refreshProfiles, rerunPreflight]);

  const updateProfile = useCallback(async (profileId: string, payload: ProfileUpdate) => {
    try {
      const updated = await profilesApi.updateProfile(profileId, payload);
      setProfiles((current) => current.map((profile) => profile.id === profileId ? updated : profile));
      await rerunPreflight();
      return updated;
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, [rerunPreflight]);

  const deleteProfile = useCallback(async (profileId: string) => {
    try {
      await profilesApi.deleteProfile(profileId);
      await Promise.all([refreshProfiles(), rerunPreflight()]);
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, [refreshProfiles, rerunPreflight]);

  const duplicateProfile = useCallback(async (profileId: string) => {
    try {
      const duplicate = await profilesApi.duplicateProfile(profileId);
      await Promise.all([refreshProfiles(), rerunPreflight()]);
      return duplicate;
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, [refreshProfiles, rerunPreflight]);

  const getProfileContext = useCallback(async (profileId: string) => {
    try {
      return await profilesApi.getProfileContext(profileId);
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      throw apiError;
    }
  }, []);

  const value = useMemo<ProfileState>(() => ({
    profiles,
    activeProfile,
    isLoading,
    error,
    refreshProfiles,
    activateProfile,
    createProfile,
    updateProfile,
    deleteProfile,
    duplicateProfile,
    getProfileContext,
    clearError: () => setError(null),
  }), [activeProfile, createProfile, deleteProfile, duplicateProfile, error, getProfileContext, isLoading, profiles, refreshProfiles, activateProfile, updateProfile]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfiles(): ProfileState {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfiles must be used within ProfileProvider');
  }
  return context;
}

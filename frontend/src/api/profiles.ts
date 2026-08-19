import { api } from './client';
import type {
  Profile,
  ProfileAutomation,
  ProfileContext,
  ProfileExportBundle,
  ProfileInput,
  ProfileTemplate,
  ProfileUpdate,
} from '../types/profiles';

interface ProfileListResponse {
  profiles: Profile[];
  total: number;
}

interface ProfileTemplateListResponse {
  templates: ProfileTemplate[];
  total: number;
}

interface ProfileAutomationListResponse {
  profile_id: string;
  automations: ProfileAutomation[];
  total: number;
}

export async function listProfiles(): Promise<ProfileListResponse> {
  return (await api.get<ProfileListResponse>('/profiles')).data;
}

export async function getProfile(profileId: string): Promise<Profile> {
  return (await api.get<Profile>(`/profiles/${profileId}`)).data;
}

export async function createProfile(payload: ProfileInput): Promise<Profile> {
  return (await api.post<Profile>('/profiles', payload)).data;
}

export async function updateProfile(profileId: string, payload: ProfileUpdate): Promise<Profile> {
  return (await api.put<Profile>(`/profiles/${profileId}`, payload)).data;
}

export async function deleteProfile(profileId: string): Promise<void> {
  await api.delete<void>(`/profiles/${profileId}`);
}

export async function duplicateProfile(profileId: string): Promise<Profile> {
  return (await api.post<Profile>(`/profiles/${profileId}/duplicate`, {})).data;
}

export async function activateProfile(profileId: string): Promise<Profile> {
  return (await api.post<Profile>(`/profiles/${profileId}/activate`, {})).data;
}

export async function listTemplates(): Promise<ProfileTemplateListResponse> {
  return (await api.get<ProfileTemplateListResponse>('/profiles/templates')).data;
}

export async function createFromTemplate(
  templateId: string,
  payload: { name?: string; activate?: boolean },
): Promise<Profile> {
  return (await api.post<Profile>(`/profiles/from-template/${templateId}`, payload)).data;
}

export async function listProfileAutomations(profileId: string): Promise<ProfileAutomationListResponse> {
  return (await api.get<ProfileAutomationListResponse>(`/profiles/${profileId}/automations`)).data;
}

export async function updateProfileAutomation(
  profileId: string,
  automationId: string,
  payload: ProfileAutomation,
): Promise<ProfileAutomation> {
  return (await api.put<ProfileAutomation>(`/profiles/${profileId}/automations/${automationId}`, payload)).data;
}

export async function getProfileContext(profileId: string): Promise<ProfileContext> {
  return (await api.get<ProfileContext>(`/profiles/${profileId}/context`)).data;
}

export async function exportProfile(profileId: string): Promise<ProfileExportBundle> {
  return (await api.get<ProfileExportBundle>(`/profiles/${profileId}/export`)).data;
}

export async function importProfile(payload: ProfileExportBundle, activate = false): Promise<Profile> {
  return (await api.post<Profile>('/profiles/import', { ...payload, activate })).data;
}

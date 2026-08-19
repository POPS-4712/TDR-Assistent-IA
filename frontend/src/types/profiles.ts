export interface Profession {
  name: string;
  sector: string;
  level: string;
}

export interface ProfileInterest {
  name: string;
  weight: number;
}

export interface ProfileLocation {
  value: string;
  country?: string | null;
  city?: string | null;
  region?: string | null;
  remote: boolean;
}

export interface ProfilePreferences {
  news_frequency: string;
  relevance_level: string;
  sources: string[];
  preferred_schedule?: string | null;
  notifications_enabled: boolean;
  additional_settings: Record<string, unknown>;
}

export interface ProfileAutomation {
  automation_id: string;
  enabled: boolean;
  configuration: Record<string, unknown>;
  updated_at?: string;
}

export interface Profile {
  id: string;
  name: string;
  description: string;
  profession: Profession;
  interests: ProfileInterest[];
  skills: string[];
  companies: string[];
  locations: ProfileLocation[];
  languages: string[];
  topics: string[];
  excluded_topics: string[];
  goals: string[];
  preferences: ProfilePreferences;
  is_active: boolean;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileInput {
  name: string;
  description: string;
  profession: Profession;
  interests: ProfileInterest[];
  skills: string[];
  companies: string[];
  locations: ProfileLocation[];
  languages: string[];
  topics: string[];
  excluded_topics: string[];
  goals: string[];
  preferences: ProfilePreferences;
  automations: ProfileAutomation[];
  is_enabled: boolean;
  activate?: boolean;
}

export type ProfileUpdate = Partial<Omit<ProfileInput, 'activate'>>;

export interface ProfileTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  data: Omit<ProfileInput, 'name' | 'description' | 'is_enabled'>;
  is_system: boolean;
}

export interface ProfileContext {
  profile_id: string;
  profile_name: string;
  profession: Profession;
  interests: ProfileInterest[];
  skills: string[];
  companies: string[];
  locations: ProfileLocation[];
  languages: string[];
  topics: string[];
  excluded_topics: string[];
  goals: string[];
  preferences: ProfilePreferences;
  automation_defaults: Record<string, Record<string, unknown>>;
}

export interface ProfileExportBundle {
  schema_version: string;
  exported_at: string;
  profile: ProfileInput;
}

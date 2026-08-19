import { useEffect, useState } from 'react';
import type { Profile, ProfileUpdate } from '../../types/profiles';
import { GoalSelector } from './GoalSelector';
import { InterestSelector } from './InterestSelector';
import { ProfileAutomationSettings } from './ProfileAutomationSettings';

interface ProfileEditorProps {
  profile: Profile;
  onSave: (profileId: string, payload: ProfileUpdate) => Promise<void>;
  onClose: () => void;
}

export function ProfileEditor({ profile, onSave, onClose }: ProfileEditorProps) {
  const [draft, setDraft] = useState<ProfileUpdate>({});
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setDraft({
      name: profile.name,
      description: profile.description,
      profession: profile.profession,
      interests: profile.interests,
      skills: profile.skills,
      companies: profile.companies,
      locations: profile.locations,
      languages: profile.languages,
      topics: profile.topics,
      excluded_topics: profile.excluded_topics,
      goals: profile.goals,
      preferences: profile.preferences,
      is_enabled: profile.is_enabled,
    });
  }, [profile]);

  const set = (changes: ProfileUpdate) => setDraft((current) => ({ ...current, ...changes }));
  const setTags = (key: 'skills' | 'companies' | 'languages' | 'topics' | 'excluded_topics', value: string) => {
    set({ [key]: value.split(',').map((item) => item.trim()).filter(Boolean) } as ProfileUpdate);
  };

  const save = async () => {
    setIsSaving(true);
    setError('');
    try {
      await onSave(profile.id, draft);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo guardar el perfil.');
    } finally {
      setIsSaving(false);
    }
  };

  const profession = draft.profession ?? profile.profession;
  const preferences = draft.preferences ?? profile.preferences;

  return (
    <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-start justify-between border-b border-gray-100 p-6"><div><p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Editar perfil</p><h2 className="mt-1 text-xl font-bold text-gray-900">{profile.name}</h2><p className="mt-1 text-sm text-gray-500">Los datos se guardan localmente y no incluyen cuentas ni credenciales.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100" aria-label="Cerrar editor">×</button></div>
      <div className="space-y-7 p-6">
        <div className="grid gap-4 md:grid-cols-2"><LabeledInput label="Nombre" value={draft.name ?? ''} onChange={(value) => set({ name: value })} /><LabeledInput label="Descripción" value={draft.description ?? ''} onChange={(value) => set({ description: value })} /></div>
        <div><h3 className="mb-3 text-base font-semibold text-gray-900">Profesión</h3><div className="grid gap-4 md:grid-cols-3"><LabeledInput label="Profesión" value={profession.name} onChange={(value) => set({ profession: { ...profession, name: value } })} /><LabeledInput label="Sector" value={profession.sector} onChange={(value) => set({ profession: { ...profession, sector: value } })} /><LabeledInput label="Nivel" value={profession.level} onChange={(value) => set({ profession: { ...profession, level: value } })} /></div></div>
        <div><h3 className="mb-3 text-base font-semibold text-gray-900">Intereses y objetivos</h3><InterestSelector interests={draft.interests ?? []} onChange={(interests) => set({ interests })} /><div className="mt-5"><GoalSelector goals={draft.goals ?? []} onChange={(goals) => set({ goals })} /></div></div>
        <div><h3 className="mb-3 text-base font-semibold text-gray-900">Etiquetas y filtros</h3><div className="grid gap-4 md:grid-cols-2"><LabeledInput label="Habilidades (separadas por comas)" value={(draft.skills ?? []).join(', ')} onChange={(value) => setTags('skills', value)} /><LabeledInput label="Empresas" value={(draft.companies ?? []).join(', ')} onChange={(value) => setTags('companies', value)} /><LabeledInput label="Ubicaciones" value={(draft.locations ?? []).map((item) => item.value).join(', ')} onChange={(value) => set({ locations: value.split(',').map((item) => item.trim()).filter(Boolean).map((item) => ({ value: item, remote: false })) })} /><LabeledInput label="Idiomas" value={(draft.languages ?? []).join(', ')} onChange={(value) => setTags('languages', value)} /><LabeledInput label="Temas" value={(draft.topics ?? []).join(', ')} onChange={(value) => setTags('topics', value)} /><LabeledInput label="Temas excluidos" value={(draft.excluded_topics ?? []).join(', ')} onChange={(value) => setTags('excluded_topics', value)} /></div></div>
        <div><h3 className="mb-3 text-base font-semibold text-gray-900">Preferencias</h3><div className="grid gap-4 md:grid-cols-3"><label className="grid gap-1.5 text-sm font-medium text-gray-700">Frecuencia<select value={preferences.news_frequency} onChange={(event) => set({ preferences: { ...preferences, news_frequency: event.target.value } })} className="input"><option value="daily">Diaria</option><option value="weekly">Semanal</option><option value="monthly">Mensual</option></select></label><label className="grid gap-1.5 text-sm font-medium text-gray-700">Relevancia<select value={preferences.relevance_level} onChange={(event) => set({ preferences: { ...preferences, relevance_level: event.target.value } })} className="input"><option value="high">Alta</option><option value="medium">Media</option><option value="low">Baja</option></select></label><LabeledInput label="Fuentes" value={preferences.sources.join(', ')} onChange={(value) => set({ preferences: { ...preferences, sources: value.split(',').map((item) => item.trim()).filter(Boolean) } })} /><LabeledInput label="Horario" value={preferences.preferred_schedule ?? ''} onChange={(value) => set({ preferences: { ...preferences, preferred_schedule: value } })} /><label className="flex items-end gap-2 pb-2 text-sm text-gray-700"><input type="checkbox" checked={preferences.notifications_enabled} onChange={(event) => set({ preferences: { ...preferences, notifications_enabled: event.target.checked } })} className="h-4 w-4" /> Notificaciones</label><label className="flex items-end gap-2 pb-2 text-sm text-gray-700"><input type="checkbox" checked={draft.is_enabled ?? true} onChange={(event) => set({ is_enabled: event.target.checked })} className="h-4 w-4" /> Perfil habilitado</label></div></div>
        <ProfileAutomationSettings profileId={profile.id} />
        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">Cancelar</button><button type="button" onClick={() => { void save(); }} disabled={isSaving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{isSaving ? 'Guardando…' : 'Guardar cambios'}</button></div>
    </section>
  );
}

function LabeledInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="grid gap-1.5 text-sm font-medium text-gray-700"><span>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} className="input" /></label>;
}

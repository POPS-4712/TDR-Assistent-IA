import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import * as profilesApi from '../../api/profiles';
import { useProfiles } from '../../contexts/ProfileContext';
import type { Profile, ProfileExportBundle, ProfileInput, ProfileTemplate, ProfileUpdate } from '../../types/profiles';
import { ProfileEditor } from './ProfileEditor';
import { ProfileList } from './ProfileList';
import { ProfileTemplateSelector } from './ProfileTemplateSelector';
import { ProfileWizard } from './ProfileWizard';

export function Profiles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { profiles, isLoading, error, clearError, createProfile, updateProfile, deleteProfile, duplicateProfile, activateProfile, refreshProfiles } = useProfiles();
  const [templates, setTemplates] = useState<ProfileTemplate[]>([]);
  const [mode, setMode] = useState<'list' | 'templates' | 'wizard' | 'editor'>(searchParams.get('create') === '1' ? 'templates' : 'list');
  const [selectedTemplate, setSelectedTemplate] = useState<ProfileTemplate | undefined>();
  const [selectedProfile, setSelectedProfile] = useState<Profile | undefined>();
  const [notice, setNotice] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await profilesApi.listTemplates();
        setTemplates(response.templates);
      } catch {
        setNotice('No se pudieron cargar las plantillas por el momento.');
      }
    };
    void loadTemplates();
  }, []);

  const showTemplates = () => {
    setSelectedProfile(undefined);
    setSelectedTemplate(undefined);
    setMode('templates');
    setSearchParams({ create: '1' });
  };

  const closeDetail = () => {
    setMode('list');
    setSelectedProfile(undefined);
    setSelectedTemplate(undefined);
    setSearchParams({});
  };

  const create = async (payload: ProfileInput) => {
    const created = await createProfile(payload);
    setNotice(`Perfil «${created.name}» creado correctamente.`);
    closeDetail();
  };

  const update = async (profileId: string, payload: ProfileUpdate) => {
    const updated = await updateProfile(profileId, payload);
    setNotice(`Perfil «${updated.name}» actualizado.`);
  };

  const exportProfile = async (profile: Profile) => {
    try {
      const bundle = await profilesApi.exportProfile(profile.id);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${profile.name.trim().replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'profile'}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice('Perfil exportado sin credenciales ni secretos.');
    } catch {
      setNotice('No se pudo exportar el perfil.');
    }
  };

  const importProfile = async (file?: File) => {
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text()) as ProfileExportBundle;
      const restored = await profilesApi.importProfile(payload);
      await refreshProfiles();
      setNotice(`Perfil «${restored.name}» restaurado correctamente.`);
    } catch {
      setNotice('El archivo no es un perfil válido o contiene datos no permitidos.');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const remove = async (profile: Profile) => {
    if (!window.confirm(`¿Eliminar el perfil «${profile.name}»? Solo se eliminarán sus preferencias y configuraciones; las credenciales no se modificarán.`)) return;
    try {
      await deleteProfile(profile.id);
      setNotice(`Perfil «${profile.name}» eliminado.`);
      if (selectedProfile?.id === profile.id) closeDetail();
    } catch {
      setNotice('No se pudo eliminar el perfil.');
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Personalización</p><h1 className="mt-1 text-2xl font-bold text-gray-900">Perfiles</h1><p className="mt-1 max-w-2xl text-gray-500">Define contextos profesionales o personales. El perfil modifica filtros y configuración de automatizaciones sin crear workflows ni duplicar credenciales.</p></div><div className="flex flex-wrap gap-2"><input ref={fileInputRef} type="file" accept="application/json,.json" className="hidden" onChange={(event) => { void importProfile(event.target.files?.[0]); }} /><button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Importar</button><button type="button" onClick={showTemplates} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Crear perfil</button></div></header>
      {(notice || error) && <div className={`rounded-lg p-3 text-sm ${error ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}><div className="flex justify-between gap-4"><span>{error?.getUserMessage() ?? notice}</span><button type="button" onClick={() => { setNotice(''); clearError(); }} aria-label="Cerrar mensaje">×</button></div></div>}
      {isLoading && mode === 'list' ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-64 animate-pulse rounded-xl bg-gray-200" />)}</div> : null}
      {mode === 'list' && !isLoading && <ProfileList profiles={profiles} onCreate={showTemplates} onSelect={(profile) => { setSelectedProfile(profile); setMode('editor'); }} onActivate={(profile) => { void activateProfile(profile.id).then(() => setNotice(`Perfil activo: ${profile.name}`)); }} onDuplicate={(profile) => { void duplicateProfile(profile.id).then((duplicate) => setNotice(`Perfil duplicado: ${duplicate.name}`)); }} onExport={(profile) => { void exportProfile(profile); }} onDelete={(profile) => { void remove(profile); }} />}
      {mode === 'templates' && <ProfileTemplateSelector templates={templates} onSelectTemplate={(template) => { setSelectedTemplate(template); setMode('wizard'); }} onStartFromScratch={() => { setSelectedTemplate(undefined); setMode('wizard'); }} />}
      {mode === 'wizard' && <ProfileWizard template={selectedTemplate} onSubmit={create} onCancel={closeDetail} />}
      {mode === 'editor' && selectedProfile && <ProfileEditor profile={selectedProfile} onSave={update} onClose={closeDetail} />}
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { useProfiles } from '../../contexts/ProfileContext';

interface ProfileSelectorProps {
  compact?: boolean;
}

export function ProfileSelector({ compact = false }: ProfileSelectorProps) {
  const navigate = useNavigate();
  const { profiles, activeProfile, activateProfile, isLoading } = useProfiles();

  const handleChange = async (profileId: string) => {
    if (profileId === '__create__') {
      navigate('/profiles?create=1');
      return;
    }
    if (profileId && profileId !== activeProfile?.id) {
      await activateProfile(profileId);
    }
  };

  return (
    <label className={`flex items-center gap-2 text-sm ${compact ? '' : 'rounded-lg border border-gray-200 bg-white p-3'}`}>
      {!compact && <span className="font-medium text-gray-700">Perfil activo</span>}
      <select
        aria-label="Seleccionar perfil activo"
        value={activeProfile?.id ?? ''}
        disabled={isLoading}
        onChange={(event) => { void handleChange(event.target.value); }}
        className="min-w-0 flex-1 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-gray-100"
      >
        <option value="" disabled>{isLoading ? 'Cargando perfiles…' : 'Seleccionar perfil'}</option>
        {profiles.filter((profile) => profile.is_enabled).map((profile) => (
          <option key={profile.id} value={profile.id}>{profile.name}</option>
        ))}
        <option value="__create__">+ Crear perfil</option>
      </select>
    </label>
  );
}

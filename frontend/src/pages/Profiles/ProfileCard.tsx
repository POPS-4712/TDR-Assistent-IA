import type { Profile } from '../../types/profiles';

interface ProfileCardProps {
  profile: Profile;
  onSelect: (profile: Profile) => void;
  onActivate: (profile: Profile) => void;
  onDuplicate: (profile: Profile) => void;
  onExport: (profile: Profile) => void;
  onDelete: (profile: Profile) => void;
}

export function ProfileCard({ profile, onSelect, onActivate, onDuplicate, onExport, onDelete }: ProfileCardProps) {
  return (
    <article className={`rounded-xl border bg-white p-5 shadow-sm transition ${profile.is_active ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200 hover:border-gray-300'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-lg font-semibold text-gray-900">{profile.name}</h3>
            {profile.is_active && <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">Activo</span>}
            {!profile.is_enabled && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">Desactivado</span>}
          </div>
          <p className="mt-1 text-sm text-gray-600">{[profile.profession.sector, profile.profession.level].filter(Boolean).join(' · ') || profile.profession.name || 'Perfil personalizado'}</p>
        </div>
        <button type="button" onClick={() => onSelect(profile)} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-800" aria-label={`Editar ${profile.name}`}>✎</button>
      </div>
      {profile.description && <p className="mt-3 line-clamp-2 text-sm text-gray-500">{profile.description}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        {profile.interests.slice(0, 3).map((interest) => <span key={interest.name} className="rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-700">{interest.name}</span>)}
        {profile.goals.slice(0, 2).map((goal) => <span key={goal} className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600">{goal}</span>)}
      </div>
      <div className="mt-5 flex flex-wrap gap-2 border-t border-gray-100 pt-4">
        {!profile.is_active && profile.is_enabled && <button type="button" onClick={() => onActivate(profile)} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">Activar</button>}
        <button type="button" onClick={() => onSelect(profile)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">Editar</button>
        <button type="button" onClick={() => onDuplicate(profile)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">Duplicar</button>
        <button type="button" onClick={() => onExport(profile)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">Exportar</button>
        <button type="button" onClick={() => onDelete(profile)} className="ml-auto rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50">Eliminar</button>
      </div>
    </article>
  );
}

import type { Profile } from '../../types/profiles';
import { ProfileCard } from './ProfileCard';

interface ProfileListProps {
  profiles: Profile[];
  onSelect: (profile: Profile) => void;
  onActivate: (profile: Profile) => void;
  onDuplicate: (profile: Profile) => void;
  onExport: (profile: Profile) => void;
  onDelete: (profile: Profile) => void;
  onCreate: () => void;
}

export function ProfileList({ profiles, onSelect, onActivate, onDuplicate, onExport, onDelete, onCreate }: ProfileListProps) {
  if (profiles.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-xl text-blue-700">◎</div>
        <h2 className="mt-4 text-lg font-semibold text-gray-900">Todavía no hay perfiles</h2>
        <p className="mx-auto mt-2 max-w-lg text-sm text-gray-500">Crea un perfil para que las automatizaciones consuman tu contexto, filtros y preferencias sin duplicar workflows ni credenciales.</p>
        <button type="button" onClick={onCreate} className="mt-5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Crear primer perfil</button>
      </section>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {profiles.map((profile) => <ProfileCard key={profile.id} profile={profile} onSelect={onSelect} onActivate={onActivate} onDuplicate={onDuplicate} onExport={onExport} onDelete={onDelete} />)}
    </div>
  );
}

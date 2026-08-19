import { useNavigate } from 'react-router-dom';
import { useProfiles } from '../../contexts/ProfileContext';

export function ActiveProfileCard() {
  const navigate = useNavigate();
  const { activeProfile, isLoading } = useProfiles();

  if (isLoading) {
    return <div className="h-44 animate-pulse rounded-xl bg-gray-200" />;
  }

  if (!activeProfile) {
    return (
      <article className="rounded-xl border border-dashed border-gray-300 bg-white p-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Perfil activo</p>
        <h2 className="mt-2 text-lg font-semibold text-gray-900">Aún no has seleccionado un perfil</h2>
        <p className="mt-1 text-sm text-gray-500">Crea un perfil para aplicar contexto a tus automatizaciones sin modificar credenciales.</p>
        <button type="button" onClick={() => navigate('/profiles?create=1')} className="mt-4 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">Crear perfil</button>
      </article>
    );
  }

  return (
    <article className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Perfil activo</p><h2 className="mt-1 text-xl font-bold text-gray-900">{activeProfile.name}</h2><p className="mt-1 text-sm text-gray-600">{[activeProfile.profession.sector, activeProfile.profession.level].filter(Boolean).join(' · ') || activeProfile.profession.name || 'Perfil personalizado'}</p></div><span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-lg text-white">◎</span></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2"><div><p className="text-xs font-medium uppercase tracking-wide text-gray-500">Intereses</p><p className="mt-1 text-sm text-gray-700">{activeProfile.interests.slice(0, 3).map((item) => item.name).join(' · ') || 'Sin definir'}</p></div><div><p className="text-xs font-medium uppercase tracking-wide text-gray-500">Objetivos</p><p className="mt-1 text-sm text-gray-700">{activeProfile.goals.slice(0, 3).join(' · ') || 'Sin definir'}</p></div></div>
      <button type="button" onClick={() => navigate('/profiles')} className="mt-4 text-sm font-semibold text-blue-700 hover:text-blue-900">Cambiar o editar perfil →</button>
    </article>
  );
}

import { useMemo, useState } from 'react';
import type { ProfileInput, ProfileLocation, ProfileTemplate } from '../../types/profiles';
import { GoalSelector } from './GoalSelector';
import { InterestSelector } from './InterestSelector';

const STEPS = ['Nombre', 'Profesión', 'Sector', 'Intereses', 'Objetivos', 'Ubicación', 'Idiomas', 'Preferencias'];

function blankProfile(): ProfileInput {
  return {
    name: '', description: '',
    profession: { name: '', sector: '', level: '' },
    interests: [], skills: [], companies: [], locations: [], languages: [], topics: [], excluded_topics: [], goals: [],
    preferences: { news_frequency: 'daily', relevance_level: 'high', sources: [], preferred_schedule: '', notifications_enabled: true, additional_settings: {} },
    automations: [], is_enabled: true, activate: true,
  };
}

function profileFromTemplate(template?: ProfileTemplate): ProfileInput {
  if (!template) return blankProfile();
  return {
    ...blankProfile(),
    ...template.data,
    name: template.name,
    description: template.description,
    is_enabled: true,
    activate: true,
  };
}

interface ProfileWizardProps {
  template?: ProfileTemplate;
  onSubmit: (profile: ProfileInput) => Promise<void>;
  onCancel: () => void;
}

export function ProfileWizard({ template, onSubmit, onCancel }: ProfileWizardProps) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<ProfileInput>(() => profileFromTemplate(template));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [location, setLocation] = useState<ProfileLocation>({ value: '', country: '', city: '', region: '', remote: false });
  const isLastStep = step === STEPS.length - 1;
  const canContinue = useMemo(() => step !== 0 || profile.name.trim().length > 0, [profile.name, step]);

  const update = (changes: Partial<ProfileInput>) => setProfile((current) => ({ ...current, ...changes }));
  const updateProfession = (changes: Partial<ProfileInput['profession']>) => setProfile((current) => ({ ...current, profession: { ...current.profession, ...changes } }));

  const addLocation = () => {
    const value = location.value.trim() || [location.city, location.region, location.country].filter(Boolean).join(', ');
    if (!value || profile.locations.some((item) => item.value.toLocaleLowerCase() === value.toLocaleLowerCase())) return;
    update({ locations: [...profile.locations, { ...location, value }] });
    setLocation({ value: '', country: '', city: '', region: '', remote: false });
  };

  const submit = async () => {
    setIsSaving(true);
    setError('');
    try {
      await onSubmit({ ...profile, name: profile.name.trim() });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo crear el perfil.');
      setIsSaving(false);
    }
  };

  const next = () => {
    if (!canContinue) return;
    if (isLastStep) { void submit(); return; }
    setStep((current) => current + 1);
  };

  return (
    <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-6 py-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Asistente de perfil</p>
        <div className="mt-1 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="text-xl font-bold text-gray-900">{template ? `Personaliza ${template.name}` : 'Crea tu perfil'}</h2>
          <span className="text-sm text-gray-500">Paso {step + 1} de {STEPS.length}</span>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-100"><div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div>
      </div>

      <div className="p-6">
        <h3 className="mb-1 text-lg font-semibold text-gray-900">{STEPS[step]}</h3>
        <p className="mb-5 text-sm text-gray-500">{step === 0 && 'Asigna un nombre reconocible y una breve descripción.'}{step === 1 && 'La profesión es un campo libre y no condiciona la plataforma.'}{step === 2 && 'Indica un sector y nivel; ambos valores pueden ser personalizados.'}{step === 3 && 'Añade intereses y define su relevancia de uno a diez.'}{step === 4 && 'Selecciona los resultados que esperas de tus automatizaciones.'}{step === 5 && 'Añade las ubicaciones relevantes para oportunidades y filtros.'}{step === 6 && 'Indica los idiomas preferidos para contenido y contexto.'}{step === 7 && 'Define cómo quieres recibir contenido personalizado.'}</p>

        {step === 0 && <div className="grid gap-4"><Field label="Nombre del perfil"><input value={profile.name} onChange={(event) => update({ name: event.target.value })} placeholder="Mi perfil profesional" className="input" autoFocus /></Field><Field label="Descripción"><textarea value={profile.description} onChange={(event) => update({ description: event.target.value })} rows={3} placeholder="Contexto y enfoque de este perfil" className="input" /></Field></div>}
        {step === 1 && <Field label="Profesión"><input value={profile.profession.name} onChange={(event) => updateProfession({ name: event.target.value })} placeholder="Abogado, Economista, Ingeniero Aeroespacial…" className="input" autoFocus /></Field>}
        {step === 2 && <div className="grid gap-4 sm:grid-cols-2"><Field label="Sector"><input value={profile.profession.sector} onChange={(event) => updateProfession({ sector: event.target.value })} placeholder="Legal, Finance, Technology…" className="input" /></Field><Field label="Nivel"><input value={profile.profession.level} onChange={(event) => updateProfession({ level: event.target.value })} placeholder="Student, Junior, Senior…" className="input" /></Field></div>}
        {step === 3 && <InterestSelector interests={profile.interests} onChange={(interests) => update({ interests })} />}
        {step === 4 && <GoalSelector goals={profile.goals} onChange={(goals) => update({ goals })} />}
        {step === 5 && <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><Field label="Ciudad"><input value={location.city ?? ''} onChange={(event) => setLocation({ ...location, city: event.target.value, value: event.target.value })} placeholder="Madrid" className="input" /></Field><Field label="País"><input value={location.country ?? ''} onChange={(event) => setLocation({ ...location, country: event.target.value })} placeholder="España" className="input" /></Field><Field label="Región"><input value={location.region ?? ''} onChange={(event) => setLocation({ ...location, region: event.target.value })} placeholder="Europa" className="input" /></Field><label className="flex items-end gap-2 pb-2 text-sm text-gray-700"><input type="checkbox" checked={location.remote} onChange={(event) => setLocation({ ...location, remote: event.target.checked })} className="h-4 w-4" /> Trabajo remoto</label></div><button type="button" onClick={addLocation} className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200">Añadir ubicación</button><TagList items={profile.locations.map((item) => item.value)} onRemove={(value) => update({ locations: profile.locations.filter((item) => item.value !== value) })} /></div>}
        {step === 6 && <TagField label="Idiomas" value={profile.languages} onChange={(languages) => update({ languages })} placeholder="Español, Inglés, Francés" />}
        {step === 7 && <div className="grid gap-4 sm:grid-cols-2"><Field label="Frecuencia de noticias"><select value={profile.preferences.news_frequency} onChange={(event) => update({ preferences: { ...profile.preferences, news_frequency: event.target.value } })} className="input"><option value="daily">Diaria</option><option value="weekly">Semanal</option><option value="monthly">Mensual</option></select></Field><Field label="Nivel de relevancia"><select value={profile.preferences.relevance_level} onChange={(event) => update({ preferences: { ...profile.preferences, relevance_level: event.target.value } })} className="input"><option value="high">Alto</option><option value="medium">Medio</option><option value="low">Bajo</option></select></Field><TagField label="Fuentes preferidas" value={profile.preferences.sources} onChange={(sources) => update({ preferences: { ...profile.preferences, sources } })} placeholder="Fuentes oficiales, publicaciones…" /><Field label="Horario"><input value={profile.preferences.preferred_schedule ?? ''} onChange={(event) => update({ preferences: { ...profile.preferences, preferred_schedule: event.target.value } })} placeholder="09:00" className="input" /></Field><label className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={profile.preferences.notifications_enabled} onChange={(event) => update({ preferences: { ...profile.preferences, notifications_enabled: event.target.checked } })} className="h-4 w-4" /> Recibir notificaciones</label><label className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={profile.activate ?? false} onChange={(event) => update({ activate: event.target.checked })} className="h-4 w-4" /> Activar al crear</label></div>}
        {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      </div>

      <div className="flex items-center justify-between border-t border-gray-100 px-6 py-4">
        <button type="button" onClick={step === 0 ? onCancel : () => setStep((current) => current - 1)} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">{step === 0 ? 'Cancelar' : 'Atrás'}</button>
        <button type="button" disabled={!canContinue || isSaving} onClick={next} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50">{isLastStep ? (isSaving ? 'Guardando…' : 'Crear perfil') : 'Continuar'}</button>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid gap-1.5 text-sm font-medium text-gray-700"><span>{label}</span>{children}</label>;
}

function TagList({ items, onRemove }: { items: string[]; onRemove: (value: string) => void }) {
  return <div className="flex flex-wrap gap-2">{items.map((item) => <span key={item} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-800">{item}<button type="button" onClick={() => onRemove(item)} aria-label={`Eliminar ${item}`} className="font-semibold">×</button></span>)}</div>;
}

function TagField({ label, value, onChange, placeholder }: { label: string; value: string[]; onChange: (items: string[]) => void; placeholder: string }) {
  const [draft, setDraft] = useState('');
  const add = () => { const items = draft.split(',').map((item) => item.trim()).filter(Boolean); if (items.length) { onChange([...new Set([...value, ...items])]); setDraft(''); } };
  return <div className="grid gap-2 sm:col-span-2"><Field label={label}><div className="flex gap-2"><input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); add(); } }} placeholder={placeholder} className="input" /><button type="button" onClick={add} className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium hover:bg-gray-200">Añadir</button></div></Field><TagList items={value} onRemove={(item) => onChange(value.filter((valueItem) => valueItem !== item))} /></div>;
}

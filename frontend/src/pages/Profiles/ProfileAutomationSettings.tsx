import { useEffect, useMemo, useState } from 'react';
import * as profilesApi from '../../api/profiles';
import { useAutomations } from '../../hooks/useAutomations';
import type { ProfileAutomation } from '../../types/profiles';

interface ProfileAutomationSettingsProps {
  profileId: string;
}

export function ProfileAutomationSettings({ profileId }: ProfileAutomationSettingsProps) {
  const { automations } = useAutomations();
  const [settings, setSettings] = useState<ProfileAutomation[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const response = await profilesApi.listProfileAutomations(profileId);
        setSettings(response.automations);
        setDrafts(Object.fromEntries(response.automations.map((item) => [item.automation_id, JSON.stringify(item.configuration, null, 2)])));
      } catch {
        setMessage('No se pudieron cargar las preferencias de automatización.');
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, [profileId]);

  const automationOptions = useMemo(() => {
    const configured = settings.map((item) => item.automation_id);
    return Array.from(new Set([...automations.map((automation) => automation.id), ...configured]));
  }, [automations, settings]);

  const settingFor = (automationId: string) => settings.find((item) => item.automation_id === automationId) ?? {
    automation_id: automationId,
    enabled: true,
    configuration: {},
  };

  const save = async (automationId: string) => {
    const current = settingFor(automationId);
    try {
      const configuration = JSON.parse(drafts[automationId] || '{}') as Record<string, unknown>;
      const saved = await profilesApi.updateProfileAutomation(profileId, automationId, { ...current, configuration });
      setSettings((items) => [...items.filter((item) => item.automation_id !== automationId), saved]);
      setDrafts((items) => ({ ...items, [automationId]: JSON.stringify(saved.configuration, null, 2) }));
      setMessage(`Configuración de ${automationId} guardada.`);
    } catch {
      setMessage('La configuración debe ser JSON válido y no puede contener secretos.');
    }
  };

  const toggle = async (automationId: string, enabled: boolean) => {
    const current = settingFor(automationId);
    try {
      const saved = await profilesApi.updateProfileAutomation(profileId, automationId, { ...current, enabled });
      setSettings((items) => [...items.filter((item) => item.automation_id !== automationId), saved]);
    } catch {
      setMessage('No se pudo actualizar esta automatización.');
    }
  };

  if (isLoading) return <p className="text-sm text-gray-500">Cargando configuración de automatizaciones…</p>;
  if (automationOptions.length === 0) return <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">Instala o descubre automatizaciones para crear configuraciones específicas por perfil.</p>;

  return (
    <section className="space-y-3">
      <div><h3 className="text-base font-semibold text-gray-900">Automatizaciones por perfil</h3><p className="text-sm text-gray-500">Cada cambio es una configuración local por perfil; no edita workflows ni credenciales.</p></div>
      {message && <p className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700">{message}</p>}
      {automationOptions.map((automationId) => {
        const current = settingFor(automationId);
        return <article key={automationId} className="rounded-lg border border-gray-200 p-4"><div className="flex items-center justify-between gap-3"><div><p className="font-medium text-gray-800">{automations.find((item) => item.id === automationId)?.name ?? automationId}</p><p className="text-xs text-gray-500">{automationId}</p></div><label className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={current.enabled} onChange={(event) => { void toggle(automationId, event.target.checked); }} className="h-4 w-4" /> Habilitada</label></div><textarea value={drafts[automationId] ?? JSON.stringify(current.configuration, null, 2)} onChange={(event) => setDrafts((items) => ({ ...items, [automationId]: event.target.value }))} rows={6} spellCheck={false} className="mt-3 w-full rounded-lg border border-gray-300 bg-slate-950 p-3 font-mono text-xs text-slate-100 outline-none focus:border-blue-500" aria-label={`Configuración JSON de ${automationId}`} /><button type="button" onClick={() => { void save(automationId); }} className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">Guardar configuración</button></article>;
      })}
    </section>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProfiles } from '../../contexts/ProfileContext';
import { useSystem } from '../../hooks/useSystem';

const STEPS = [
  'Welcome',
  'Compatibility',
  'Local services',
  'Secure storage',
  'First profile',
  'Accounts',
  'Finish',
];

export function FirstRunWizard() {
  const navigate = useNavigate();
  const { activeProfile } = useProfiles();
  const { setupStatus, diagnostics, isLoading, completeSetup, refreshAll } = useSystem();
  const [step, setStep] = useState(0);
  const [isCompleting, setIsCompleting] = useState(false);

  const showWizard = Boolean(
    setupStatus && setupStatus.user_data_dir_configured && !setupStatus.first_run_complete,
  );
  const services = useMemo(() => Object.entries(setupStatus?.services || {}), [setupStatus]);

  useEffect(() => {
    if (showWizard) void refreshAll();
  }, [showWizard, refreshAll]);

  if (!showWizard) return null;

  const serviceReady = setupStatus?.runtime_ready === true;
  const profileReady = Boolean(activeProfile);
  const canAdvance = step === 1 ? serviceReady : step === 3 ? setupStatus?.user_data_dir_configured : step === 4 ? profileReady : true;

  const next = async () => {
    if (step === 4 && !profileReady) {
      navigate('/profiles?create=1');
      return;
    }
    if (step < STEPS.length - 1) {
      setStep((current) => current + 1);
      return;
    }
    setIsCompleting(true);
    try {
      await completeSetup();
    } finally {
      setIsCompleting(false);
    }
  };

  const content = () => {
    switch (step) {
      case 0:
        return <p>Automation Center runs locally on this device. This assistant prepares the local runtime, lets you create a first profile and leaves external accounts optional.</p>;
      case 1:
        return (
          <div className="space-y-2">
            <p>System compatibility is checked without changing any services.</p>
            <dl className="grid grid-cols-2 gap-3 rounded-lg bg-gray-50 p-3 text-sm">
              <div><dt className="text-gray-500">Platform</dt><dd className="font-medium">{diagnostics?.platform || 'Checking'}</dd></div>
              <div><dt className="text-gray-500">Architecture</dt><dd className="font-medium">{diagnostics?.architecture || 'Checking'}</dd></div>
              <div><dt className="text-gray-500">Runtime</dt><dd className="font-medium">{diagnostics?.local_service_control.message || 'Checking'}</dd></div>
              <div><dt className="text-gray-500">Free disk</dt><dd className="font-medium">{diagnostics ? `${Math.floor(diagnostics.disk.free_bytes / 1_000_000_000)} GB` : 'Checking'}</dd></div>
            </dl>
            {!serviceReady && <p className="rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">Start or repair the local runtime before continuing. No external account is required.</p>}
          </div>
        );
      case 2:
        return (
          <div className="space-y-2">
            <p>Local services are checked automatically. They stay on this device and are not exposed as Docker controls in normal mode.</p>
            <div className="space-y-2">
              {services.map(([name, state]) => <div key={name} className="flex justify-between rounded-md bg-gray-50 px-3 py-2 text-sm"><span className="capitalize">{name}</span><span className={state.status === 'healthy' ? 'text-green-700' : 'text-yellow-700'}>{state.status}</span></div>)}
            </div>
          </div>
        );
      case 3:
        return <p>Secure local storage has been initialized in your private data directory. Secret values are generated locally and are not shown, exported or bundled with the app.</p>;
      case 4:
        return profileReady
          ? <p>Your active profile is <strong>{activeProfile?.name}</strong>. It can be edited later from Profiles.</p>
          : <p>Create or select the first profile. Templates remain editable and the application does not assume a profession.</p>;
      case 5:
        return <div className="space-y-3"><p>External accounts are optional. You can connect Google, Gemini, Telegram, WhatsApp or other providers later from Accounts.</p><button type="button" onClick={() => navigate('/accounts')} className="rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50">Open Accounts</button></div>;
      default:
        return <p>Setup is ready to finish. Automations will be discovered and preflighted automatically; only workflows you explicitly install will be imported.</p>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 p-4" role="dialog" aria-modal="true" aria-labelledby="first-run-title">
      <div className="mx-auto mt-8 w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl sm:mt-16">
        <div className="mb-6 flex items-start justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-wide text-blue-700">First-run setup</p><h2 id="first-run-title" className="mt-1 text-2xl font-bold text-gray-900">{STEPS[step]}</h2></div><span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">{step + 1} / {STEPS.length}</span></div>
        <div className="mb-6 h-2 overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-blue-600 transition-all duration-200" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div>
        <div className="min-h-36 text-gray-700">{content()}</div>
        <div className="mt-6 flex items-center justify-between gap-3 border-t pt-4"><button type="button" disabled={step === 0 || isCompleting} onClick={() => setStep((current) => current - 1)} className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-40">Back</button><button type="button" disabled={!canAdvance || isCompleting || isLoading} onClick={() => void next()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50">{step === STEPS.length - 1 ? (isCompleting ? 'Finishing…' : 'Finish') : step === 4 && !profileReady ? 'Create profile' : 'Continue'}</button></div>
      </div>
    </div>
  );
}

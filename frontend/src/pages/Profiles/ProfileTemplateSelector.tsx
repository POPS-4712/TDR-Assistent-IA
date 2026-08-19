import type { ProfileTemplate } from '../../types/profiles';

const ICONS: Record<string, string> = {
  briefcase: '▣', scale: '⚖', chart: '◈', code: '⌘', tools: '⚙', rocket: '◢',
  health: '✚', flask: '⚗', megaphone: '◉', building: '▥', academic: '▤',
  news: '▧', graduation: '◇', lightbulb: '◌', profile: '●',
};

interface ProfileTemplateSelectorProps {
  templates: ProfileTemplate[];
  onSelectTemplate: (template: ProfileTemplate) => void;
  onStartFromScratch: () => void;
}

export function ProfileTemplateSelector({ templates, onSelectTemplate, onStartFromScratch }: ProfileTemplateSelectorProps) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Crear perfil</p>
        <h2 className="mt-1 text-xl font-bold text-gray-900">Elige un punto de partida</h2>
        <p className="mt-1 text-sm text-gray-500">Las plantillas solo aportan contexto inicial; podrás modificar todos los campos después.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template) => (
          <button
            type="button"
            key={template.id}
            onClick={() => onSelectTemplate(template)}
            className="rounded-xl border border-gray-200 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 text-lg text-blue-700">{ICONS[template.icon] ?? ICONS.profile}</span>
            <span className="block font-semibold text-gray-900">{template.name}</span>
            <span className="mt-1 block text-xs leading-5 text-gray-500">{template.description}</span>
          </button>
        ))}
        <button
          type="button"
          onClick={onStartFromScratch}
          className="rounded-xl border border-dashed border-gray-300 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-lg text-gray-700">+</span>
          <span className="block font-semibold text-gray-900">Empezar desde cero</span>
          <span className="mt-1 block text-xs leading-5 text-gray-500">Crea un perfil con campos libres y una configuración totalmente propia.</span>
        </button>
      </div>
    </section>
  );
}

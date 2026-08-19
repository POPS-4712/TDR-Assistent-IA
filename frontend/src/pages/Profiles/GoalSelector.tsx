const DEFAULT_GOALS = [
  'Buscar empleo',
  'Seguir noticias',
  'Investigación',
  'Personal Brand',
  'Formación',
  'Automatizar email',
  'Gestionar agenda',
];

interface GoalSelectorProps {
  goals: string[];
  onChange: (goals: string[]) => void;
}

export function GoalSelector({ goals, onChange }: GoalSelectorProps) {
  const toggleGoal = (goal: string) => {
    onChange(goals.includes(goal) ? goals.filter((item) => item !== goal) : [...goals, goal]);
  };

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {DEFAULT_GOALS.map((goal) => (
        <label key={goal} className="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:border-blue-300">
          <input type="checkbox" checked={goals.includes(goal)} onChange={() => toggleGoal(goal)} className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
          {goal}
        </label>
      ))}
    </div>
  );
}

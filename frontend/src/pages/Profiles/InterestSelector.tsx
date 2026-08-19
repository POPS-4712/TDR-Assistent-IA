import { useState } from 'react';
import type { ProfileInterest } from '../../types/profiles';

interface InterestSelectorProps {
  interests: ProfileInterest[];
  onChange: (interests: ProfileInterest[]) => void;
}

export function InterestSelector({ interests, onChange }: InterestSelectorProps) {
  const [draft, setDraft] = useState('');

  const addInterest = () => {
    const name = draft.trim();
    if (!name || interests.some((interest) => interest.name.toLocaleLowerCase() === name.toLocaleLowerCase())) return;
    onChange([...interests, { name, weight: 5 }]);
    setDraft('');
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); addInterest(); } }}
          placeholder="Añadir interés"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <button type="button" onClick={addInterest} className="rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200">Añadir</button>
      </div>
      <div className="space-y-2">
        {interests.map((interest) => (
          <div key={interest.name} className="flex items-center gap-3 rounded-lg bg-gray-50 p-2">
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-800">{interest.name}</span>
            <input
              aria-label={`Relevancia de ${interest.name}`}
              type="range"
              min="1"
              max="10"
              value={interest.weight}
              onChange={(event) => onChange(interests.map((item) => item.name === interest.name ? { ...item, weight: Number(event.target.value) } : item))}
              className="w-24 accent-blue-600"
            />
            <span className="w-5 text-right text-xs font-semibold text-blue-700">{interest.weight}</span>
            <button type="button" onClick={() => onChange(interests.filter((item) => item.name !== interest.name))} className="text-sm text-red-600 hover:text-red-800" aria-label={`Eliminar ${interest.name}`}>×</button>
          </div>
        ))}
      </div>
    </div>
  );
}

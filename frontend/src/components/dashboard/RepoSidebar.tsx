import { useState } from 'react';
import type { Repo } from '../../types';
import { useAddRepo, useDeleteRepo, useSyncRepo } from '../../api/hooks';

interface Props {
  repos: Repo[];
  isLoading: boolean;
  activeId: number | null;
  onSelect: (repo: Repo) => void;
}

export default function RepoSidebar({ repos, isLoading, activeId, onSelect }: Props) {
  const addRepo = useAddRepo();
  const deleteRepo = useDeleteRepo();
  const syncRepo = useSyncRepo();
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (!url.trim()) return;
    addRepo.mutate(url.trim());
    setUrl('');
  };

  return (
    <aside className="w-72 bg-gray-900 text-gray-100 flex flex-col h-full border-r border-gray-700">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold mb-3">🔮 YAML Wizard</h1>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-800 text-sm rounded px-2 py-1 border border-gray-600 focus:border-blue-500 outline-none"
            placeholder="GitHub repo URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <button
            className="bg-blue-600 hover:bg-blue-500 text-sm px-3 py-1 rounded disabled:opacity-50"
            onClick={handleAdd}
            disabled={addRepo.isPending}
          >
            +
          </button>
        </div>
        {addRepo.isError && (
          <p className="text-red-400 text-xs mt-1">{(addRepo.error as Error).message}</p>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto">
        {isLoading && <p className="p-4 text-sm text-gray-400">Loading...</p>}
        {repos?.map((repo) => (
          <div
            key={repo.id}
            className={`p-3 cursor-pointer border-b border-gray-800 hover:bg-gray-800 ${
              activeId === repo.id ? 'bg-gray-800 border-l-2 border-l-blue-500' : ''
            }`}
            onClick={() => onSelect(repo)}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium truncate">{repo.full_name}</span>
              <span className="text-xs text-gray-500 uppercase">{repo.platform}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-gray-400">
                {repo.last_synced_at
                  ? `Synced ${new Date(repo.last_synced_at).toLocaleTimeString()}`
                  : 'Never synced'}
              </span>
              <div className="flex gap-1">
                <button
                  className="text-xs text-blue-400 hover:text-blue-300"
                  onClick={(e) => { e.stopPropagation(); syncRepo.mutate(repo.id); }}
                  title="Sync now"
                >
                  🔄
                </button>
                <button
                  className="text-xs text-red-400 hover:text-red-300"
                  onClick={(e) => { e.stopPropagation(); deleteRepo.mutate(repo.id); }}
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            </div>
            {syncRepo.isPending && syncRepo.variables === repo.id && (
              <p className="text-xs text-yellow-400 mt-1">Syncing...</p>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}

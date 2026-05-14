import { useState } from 'react';
import type { Repo } from '../../types';
import { useAddRepo, useDeleteRepo, useSyncRepo } from '../../api/hooks';

import styles from './RepoSidebar.module.css';

interface Props {
  repos: Repo[];
  isLoading: boolean;
  activeId: number | null;
  onSelect: (repo: Repo) => void;
}

export default function RepoSidebar({
  repos,
  isLoading,
  activeId,
  onSelect,
}: Props) {
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
    <aside className={styles.repoSidebar}>
      <div className={styles.repoSidebarHeader}>
        <h1 className={styles.repoSidebarTitle}>
          YAML Wizard
        </h1>

        <div className={styles.repoSidebarInputRow}>
          <input
            className={styles.repoSidebarInput}
            placeholder="GitHub repo URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />

          <button
            className={styles.repoSidebarAddBtn}
            onClick={handleAdd}
            disabled={addRepo.isPending}
          >
            +
          </button>
        </div>

        {addRepo.isError && (
          <p className={styles.repoSidebarError}>
            {(addRepo.error as Error).message}
          </p>
        )}
      </div>

      <nav className={styles.repoSidebarNav}>
        {isLoading && (
          <p className={styles.repoSidebarLoading}>
            Loading...
          </p>
        )}

        {repos?.map((repo) => (
          <div
            key={repo.id}
            className={`${styles.repoItem} ${
              activeId === repo.id ? styles.repoItemActive : ''
            }`}
            onClick={() => onSelect(repo)}
          >
            <div className={styles.repoItemTop}>
              <span className={styles.repoItemName}>
                {repo.full_name}
              </span>

              <span className={styles.repoItemPlatform}>
                {repo.platform}
              </span>
            </div>

            <div className={styles.repoItemBottom}>
              <span className={styles.repoItemSyncText}>
                {repo.last_synced_at
                  ? `Synced ${new Date(
                      repo.last_synced_at
                    ).toLocaleTimeString()}`
                  : 'Never synced'}
              </span>

              <div className={styles.repoItemActions}>
                <button
                  className={styles.repoSyncBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    syncRepo.mutate(repo.id);
                  }}
                  title="Sync now"
                >
                  🔄
                </button>

                <button
                  className={styles.repoDeleteBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteRepo.mutate(repo.id);
                  }}
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            </div>

            {syncRepo.isPending &&
              syncRepo.variables === repo.id && (
                <p className={styles.repoSyncingText}>
                  Syncing...
                </p>
              )}
          </div>
        ))}
      </nav>
    </aside>
  );
}

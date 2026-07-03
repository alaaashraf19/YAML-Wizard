import { useMemo, useState } from 'react';
import type { Repo } from '../../types';
import logo from "../../assets/yaml_wizard_logo.png";

import { useAddRepo, useDeleteRepo, useSyncRepo, useRepoDeleteStatus } from '../../api/hooks';

import gStyles from "../../global.module.css"
import styles from './RepoSidebar.module.css';
import { useNavigate } from 'react-router-dom';

import { FiPlus, FiSearch } from 'react-icons/fi';
import { IoClose } from 'react-icons/io5';
import { MdDeleteOutline } from 'react-icons/md';
import { CgSync } from 'react-icons/cg';

interface Props {
  repos: Repo[];
  isLoading: boolean;
  activeId: number | null;
  onSelect: (repo: Repo) => void;
}
function RepoItem({
  repo,
  activeId,
  onSelect,
  syncRepo,
  deleteRepo,
}: {
  repo: Repo;
  activeId: number | null;
  onSelect: (repo: Repo) => void;
  syncRepo: ReturnType<typeof useSyncRepo>;
  deleteRepo: ReturnType<typeof useDeleteRepo>;
}) {
  const { data: deleteStatus } = useRepoDeleteStatus(repo.id);

  return (
    <div
      className={`${styles.repoItem} ${
        activeId === repo.id ? styles.repoItemActive : ""
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
            ? `Synced ${new Date(repo.last_synced_at).toLocaleTimeString()}`
            : "Never synced"}
        </span>

        <div className={styles.repoItemActions}>
          <button
            className={styles.repoSyncBtn}
            onClick={(e) => {
              e.stopPropagation();
              syncRepo.mutate(repo.id);
            }}
            disabled={syncRepo.isPending && syncRepo.variables === repo.id}
            title={
              syncRepo.isPending && syncRepo.variables === repo.id
                ? "Syncing..."
                : "Sync now"
            }
          >
            {syncRepo.isPending && syncRepo.variables === repo.id
              ? "⏳"
              : "🔄"}
          </button>

          {deleteStatus?.can_delete && (
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
          )}
        </div>
      </div>

      {syncRepo.isPending &&
        syncRepo.variables === repo.id && (
          <p className={styles.repoSyncingText}>
            Syncing...
          </p>
        )}
    </div>
  );
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
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');

  const handleAdd = () => {
    if (!url.trim()) return;

    addRepo.mutate(url.trim());
    setUrl('');
  };

  const filteredRepos = useMemo(() => {
    if (!repos) return [];
    if (!query.trim()) return repos;

    const q = query.trim().toLowerCase();
    return repos.filter((repo) =>
      repo.full_name.toLowerCase().includes(q) ||
      repo.platform.toLowerCase().includes(q)
    );
  }, [repos, query]);

  return (
    <aside className={styles.repoSidebar}>
      <div className={styles.repoSidebarHeader}>
        <div className={styles.appNameContainer}>
            <img src={logo} alt="" onClick={() => navigate("/")}
              className={`${styles.logo} ${gStyles.clickable}`}/>
            <span className={gStyles.clickable}
              onClick={() => navigate("/")}>YAML Wizard</span>
        </div>

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
            title="Add repository"
          >
            <FiPlus className={styles.btnIcon} />
          </button>
        </div>

        {addRepo.isError && (
          <p className={styles.repoSidebarError}>
            {(addRepo.error as Error).message}
          </p>
        )}

        <div className={styles.repoSidebarSearchRow}>
          <FiSearch className={styles.searchIcon} />

          <input
            className={styles.repoSidebarSearch}
            placeholder="Search repos..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          {query && (
            <IoClose
              className={`${styles.searchClearIcon} ${gStyles.clickable}`}
              onClick={() => setQuery('')}
              title="Clear search"
            />
          )}
        </div>
      </div>

      <nav className={styles.repoSidebarNav}>
        {isLoading && (
          <p className={styles.repoSidebarLoading}>
            Loading...
          </p>
        )}

        {!isLoading && repos.length > 0 && filteredRepos.length === 0 && (
          <p className={styles.repoSidebarLoading}>
            No repos match "{query}".
          </p>
        )}

        {filteredRepos.map((repo) => (
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
                  className={`${styles.repoSyncBtn} ${
                    syncRepo.isPending && syncRepo.variables === repo.id
                      ? styles.spinning
                      : ''
                  }`}
                  onClick={(e) => {
                    e.stopPropagation();
                    syncRepo.mutate(repo.id);
                  }}
                  disabled={syncRepo.isPending && syncRepo.variables === repo.id}
                  title="Sync now"
                >
                  <CgSync className={styles.btnIcon} />
                </button>

                <button
                  className={styles.repoDeleteBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteRepo.mutate(repo.id);
                  }}
                  title="Remove"
                >
                  <MdDeleteOutline className={styles.btnIcon} />
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
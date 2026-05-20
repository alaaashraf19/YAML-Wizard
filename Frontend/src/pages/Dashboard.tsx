import { useState, useMemo, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Repo, PipelineRun, TestRun } from '../types';
import { useRuns, useRun, useInsights, useRepos } from '../api/hooks';
import { useWebSocket } from '../api/websocket';

import RepoSidebar from '../components/dashboard/RepoSidebar';
import CommitTimeline from '../components/dashboard/CommitTimeline';
import PipelineStages from '../components/dashboard/PipelineStages';
import TestGrid from '../components/dashboard/TestGrid';
import TestDetail from '../components/dashboard/TestDetail';
import InsightsPanel from '../components/dashboard/InsightsPanel';
import TrendChart from '../components/dashboard/TrendChart';
import Filters from '../components/dashboard/Filters';

import styles from './Dashboard.module.css';

export default function Dashboard() {
  const queryClient = useQueryClient();

  const [activeRepo, setActiveRepo] = useState<Repo | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [branchFilter, setBranchFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data: repos, isLoading: reposLoading } = useRepos();
  const { data: runs } = useRuns(activeRepo?.id ?? null, 30);
  const { data: runDetail } = useRun(activeRepo?.id ?? null, selectedRunId);
  const { data: insights } = useInsights(activeRepo?.id ?? null, selectedRunId);

  const handleWSMessage = useCallback((msg: Record<string, unknown>) => {
    if (msg.type === 'sync_complete') {
      const repoId = msg.repo_id;
      queryClient.invalidateQueries({ queryKey: ['runs', repoId] });
      queryClient.invalidateQueries({ queryKey: ['insights', repoId] });
      queryClient.invalidateQueries({ queryKey: ['trends', repoId] });
      queryClient.invalidateQueries({ queryKey: ['repos'] });
    }
  }, [queryClient]);

  useWebSocket(activeRepo?.id ?? null, handleWSMessage);

  useEffect(() => {
    if (runs && runs.length > 0 && !selectedRunId) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  const handleSelectRepo = (repo: Repo) => {
    setActiveRepo(repo);
    setSelectedRunId(null);
    setSelectedTest(null);
    setBranchFilter('');
    setStatusFilter('');
  };

  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    let filtered = runs;
    if (branchFilter) filtered = filtered.filter((r) => r.branch === branchFilter);
    if (statusFilter) filtered = filtered.filter((r) => r.conclusion === statusFilter);
    return filtered;
  }, [runs, branchFilter, statusFilter]);

  const branches = useMemo(() => {
    if (!runs) return [];
    return [...new Set(runs.map((r) => r.branch).filter(Boolean))] as string[];
  }, [runs]);

  const handleSelectRun = (run: PipelineRun) => {
    setSelectedRunId(run.id);
    setSelectedTest(null);
  };

  const handleSelectTest = (test: TestRun) => {
    setSelectedTest(test.test_name);
  };

  return (
    <div className={styles.container}>

      <RepoSidebar
        repos={repos ?? []}
        isLoading={reposLoading}
        activeId={activeRepo?.id ?? null}
        onSelect={handleSelectRepo}
      />

      <main className={styles.main}>

        {!activeRepo ? (
          <div className={styles.center}>
            <div style={{ textAlign: 'center' }}>
              <h2 className="text-2xl font-bold mb-2">
                YAML Wizard Dashboard
              </h2>
              <p className="text-gray-400">
                Add a repository from the sidebar to get started.
              </p>
            </div>
          </div>
        ) : (
          <>
            <header className={styles.header}>
              <div>
                <h2 className="text-lg font-bold whitespace-pre-line">
                  {activeRepo.full_name.split('/').join('\n')}
                </h2>
                <span className="text-xs text-gray-400">
                  {activeRepo.platform} · {branchFilter || activeRepo.default_branch}
                </span>
              </div>

              <Filters
                branch={branchFilter}
                onBranchChange={setBranchFilter}
                statusFilter={statusFilter}
                onStatusChange={setStatusFilter}
                branches={branches}
              />
            </header>

            <div className={styles.content}>

              {runs && runs.length === 0 ? (
                <div className={styles.center}>
                  <div style={{ textAlign: 'center' }}>
                    <p className="text-5xl mb-4">📭</p>
                    <h3 className="text-lg font-semibold mb-1">
                      No pipeline runs found
                    </h3>
                    <p className="text-gray-400 text-sm max-w-md">
                      This repository has no GitHub Actions workflow runs.
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div className={styles.timeline}>
                    <CommitTimeline
                      runs={filteredRuns}
                      selectedId={selectedRunId}
                      onSelect={handleSelectRun}
                    />
                  </div>

                  <div className={styles.detail}>
                    {!runDetail ? (
                      <div className={styles.center}>
                        <p className="text-gray-400">
                          Select a run from the timeline.
                        </p>
                      </div>
                    ) : (
                      <>
                        {insights && insights.length > 0 && (
                          <InsightsPanel insights={insights} />
                        )}

                        <PipelineStages jobs={runDetail.jobs} />

                        <TestGrid
                          tests={runDetail.tests}
                          onSelect={handleSelectTest}
                        />

                        {selectedTest && activeRepo && (
                          <TestDetail
                            repoId={activeRepo.id}
                            testName={selectedTest}
                            onClose={() => setSelectedTest(null)}
                          />
                        )}

                        <TrendChart repoId={activeRepo.id} />
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
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

  // WebSocket: auto-refresh data when backend syncs new runs
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

  // Auto-select the first (latest) run when runs load or repo changes
  useEffect(() => {
    if (runs && runs.length > 0 && !selectedRunId) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  // Reset selection when switching repos
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
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <RepoSidebar
        repos={repos ?? []}
        isLoading={reposLoading}
        activeId={activeRepo?.id ?? null}
        onSelect={handleSelectRepo}
      />

      <main className="flex-1 overflow-hidden flex flex-col">
        {!activeRepo ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">🔮 YAML Wizard Dashboard</h2>
              <p className="text-gray-400">Add a repository from the sidebar to get started.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <header className="p-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold">{activeRepo.full_name}</h2>
                <span className="text-xs text-gray-400">
                  {activeRepo.platform} · {activeRepo.default_branch}
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

            {/* Content */}
            <div className="flex-1 overflow-hidden flex">
              {runs && runs.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-5xl mb-4">📭</p>
                    <h3 className="text-lg font-semibold mb-1">No pipeline runs found</h3>
                    <p className="text-gray-400 text-sm max-w-md">
                      This repository has no GitHub Actions workflow runs.
                      Make sure the repo has a <code className="bg-gray-800 px-1 rounded">.github/workflows/</code> directory
                      with at least one completed run.
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  {/* Left: Commit Timeline */}
                  <div className="w-80 border-r border-gray-800 overflow-y-auto p-3">
                    <CommitTimeline
                      runs={filteredRuns}
                      selectedId={selectedRunId}
                      onSelect={handleSelectRun}
                    />
                  </div>

                  {/* Right: Run detail */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {!runDetail ? (
                      <div className="flex items-center justify-center h-full">
                        <p className="text-gray-400">Select a run from the timeline.</p>
                      </div>
                    ) : (
                      <>
                        {/* Insights */}
                        {insights && insights.length > 0 && (
                          <InsightsPanel insights={insights} />
                        )}

                        {/* Pipeline Stages */}
                        <PipelineStages jobs={runDetail.jobs} />

                        {/* Test Grid */}
                        <TestGrid tests={runDetail.tests} onSelect={handleSelectTest} />

                        {/* Test Detail (expanded) */}
                        {selectedTest && activeRepo && (
                          <TestDetail
                            repoId={activeRepo.id}
                            testName={selectedTest}
                            onClose={() => setSelectedTest(null)}
                          />
                        )}

                        {/* Trend Chart */}
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

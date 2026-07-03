import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export function useRepos() {
  return useQuery({ queryKey: ['repos'], queryFn: api.listRepos });
}

export function useAddRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => api.addRepo(url),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['repos'] }),
  });
}

export function useDeleteRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteRepo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['repos'] }),
  });
}
export function useRepoDeleteStatus(repoId: number | null) {
  return useQuery({
    queryKey: ['repoDeleteStatus', repoId],
    queryFn: () => api.getRepoDeleteStatus(repoId!),
    enabled: !!repoId,
  });
}
export function useSyncRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.syncRepo(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['runs', id] });
      qc.invalidateQueries({ queryKey: ['insights', id], exact: false });
      qc.invalidateQueries({ queryKey: ['trends', id] });
      qc.invalidateQueries({ queryKey: ['branches', id] });
      qc.invalidateQueries({ queryKey: ['repos'] });
    },
  });
}

export function useRuns(repoId: number | null, limit = 20) {
  return useQuery({
    queryKey: ['runs', repoId, limit],
    queryFn: () => api.listRuns(repoId!, limit),
    enabled: !!repoId,
    refetchInterval: 120_000, // Poll every 2 min as fallback if WS fails
  });
}

export function useLatestRun(repoId: number | null) {
  return useQuery({
    queryKey: ['latestRun', repoId],
    queryFn: () => api.getLatestRun(repoId!),
    enabled: !!repoId,
  });
}

export function useBranches(repoId: number | null) {
  return useQuery({
    queryKey: ['branches', repoId],
    queryFn: () => api.getBranches(repoId!),
    enabled: !!repoId,
  });
}

export function useRun(repoId: number | null, runId: number | null) {
  return useQuery({
    queryKey: ['run', repoId, runId],
    queryFn: () => api.getRun(repoId!, runId!),
    enabled: !!repoId && !!runId,
  });
}

export function useInsights(repoId: number | null, runId: number | null = null) {
  return useQuery({
    queryKey: ['insights', repoId, runId],
    queryFn: () => api.getInsights(repoId!, runId ?? undefined),
    enabled: !!repoId,
  });
}

export function useTrends(repoId: number | null, limit = 20) {
  return useQuery({
    queryKey: ['trends', repoId, limit],
    queryFn: () => api.getTrends(repoId!, limit),
    enabled: !!repoId,
  });
}

export function useTestHistory(repoId: number | null, testName: string | null) {
  return useQuery({
    queryKey: ['testHistory', repoId, testName],
    queryFn: () => api.getTestHistory(repoId!, testName!),
    enabled: !!repoId && !!testName && testName.length > 0,
  });
}

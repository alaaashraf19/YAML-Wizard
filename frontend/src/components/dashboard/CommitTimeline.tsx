import type { PipelineRun } from '../../types';

interface Props {
  runs: PipelineRun[];
  selectedId: number | null;
  onSelect: (run: PipelineRun) => void;
}

function statusIcon(conclusion: string | null) {
  switch (conclusion) {
    case 'success': return '✅';
    case 'failure': return '❌';
    case 'cancelled': return '⚪';
    default: return '⏳';
  }
}

function formatDuration(seconds: number | null) {
  if (seconds === null) return '—';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function timeAgo(dateStr: string | null) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function CommitTimeline({ runs, selectedId, onSelect }: Props) {
  if (!runs.length) {
    return <p className="text-gray-400 text-sm p-4">No runs synced yet. Click 🔄 to sync.</p>;
  }

  return (
    <div className="space-y-1">
      <h2 className="text-sm font-semibold text-gray-300 mb-2 px-1">Recent Runs</h2>
      {runs.map((run) => {
        const diffPct = run.compared_to_prev_pct;
        const diffStr = diffPct !== null
          ? `${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}%`
          : null;
        const diffColor = diffPct !== null
          ? diffPct > 20 ? 'text-red-400' : diffPct > 0 ? 'text-yellow-400' : 'text-green-400'
          : '';

        return (
          <div
            key={run.id}
            className={`p-3 rounded cursor-pointer transition-colors ${
              selectedId === run.id
                ? 'bg-blue-900/40 border border-blue-600'
                : 'bg-gray-800/50 hover:bg-gray-800 border border-transparent'
            }`}
            onClick={() => onSelect(run)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-base">{statusIcon(run.conclusion)}</span>
                <code className="text-xs text-blue-400 font-mono">{run.commit_hash.slice(0, 7)}</code>
                {run.branch && (
                  <span className="text-xs bg-gray-700 rounded px-1.5 py-0.5 text-gray-300 truncate max-w-24">
                    {run.branch}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400 shrink-0">
                <span>{formatDuration(run.total_duration_s)}</span>
                {diffStr && <span className={diffColor}>{diffStr}</span>}
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1 truncate">
              {run.commit_message || 'No message'}
            </p>
            <span className="text-xs text-gray-500">{timeAgo(run.started_at)}</span>
          </div>
        );
      })}
    </div>
  );
}

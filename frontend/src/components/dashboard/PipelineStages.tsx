import type { JobTiming } from '../../types';

interface Props {
  jobs: JobTiming[];
}

function statusIcon(status: string) {
  switch (status) {
    case 'success': return '✅';
    case 'failure': return '❌';
    case 'skipped': return '⏭️';
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

export default function PipelineStages({ jobs }: Props) {
  if (!jobs.length) {
    return <p className="text-gray-400 text-sm">No job data available.</p>;
  }

  const maxDuration = Math.max(...jobs.map((j) => j.duration_s || 0), 1);

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 mb-2">Pipeline Stages</h2>
      <div className="space-y-2">
        {jobs.map((job) => {
          const widthPct = job.duration_s ? (job.duration_s / maxDuration) * 100 : 0;
          const diffPct = job.compared_to_prev_pct;
          const diffStr = diffPct !== null
            ? `${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}%`
            : null;
          const barColor =
            job.status === 'failure' ? 'bg-red-600' :
            (diffPct && diffPct > 20) ? 'bg-yellow-600' : 'bg-green-600';

          return (
            <div key={job.id} className="bg-gray-800/50 rounded p-2">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span>{statusIcon(job.status)}</span>
                  <span className="text-sm text-gray-200">{job.job_name}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-300">{formatDuration(job.duration_s)}</span>
                  {diffStr && (
                    <span className={diffPct! > 20 ? 'text-red-400' : diffPct! > 0 ? 'text-yellow-400' : 'text-green-400'}>
                      {diffStr}
                    </span>
                  )}
                </div>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className={`${barColor} h-2 rounded-full transition-all duration-500`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

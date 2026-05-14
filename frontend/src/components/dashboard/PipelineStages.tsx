import type { JobTiming } from '../../types';
import styles from './PipelineStages.module.css';

interface Props {
  jobs: JobTiming[];
}

function statusIcon(status: string) {
  switch (status) {
    case 'success':
      return '✅';
    case 'failure':
      return '❌';
    case 'skipped':
      return '⏭️';
    case 'cancelled':
      return '⚪';
    default:
      return '⏳';
  }
}

function formatDuration(seconds: number | null) {
  if (seconds === null) return '—';
  if (seconds < 60) return `${seconds}s`;

  const m = Math.floor(seconds / 60);
  const s = seconds % 60;

  return `${m}m ${s}s`;
}

export default function PipelineStages({
  jobs,
}: Props) {
  if (!jobs.length) {
    return (
      <p className={styles.empty}>
        No job data available.
      </p>
    );
  }

  const maxDuration = Math.max(
    ...jobs.map((j) => j.duration_s || 0),
    1
  );

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>
        Pipeline Stages
      </h2>

      <div className={styles.list}>
        {jobs.map((job) => {
          const widthPct = job.duration_s
            ? (job.duration_s / maxDuration) *
              100
            : 0;

          const diffPct =
            job.compared_to_prev_pct;

          const diffStr =
            diffPct !== null
              ? `${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}%`
              : null;

          const barColor =
            job.status === 'failure'
              ? styles.barRed
              : diffPct && diffPct > 20
              ? styles.barYellow
              : styles.barGreen;

          const diffColor =
            diffPct! > 20
              ? styles.diffRed
              : diffPct! > 0
              ? styles.diffYellow
              : styles.diffGreen;

          return (
            <div
              key={job.id}
              className={styles.card}
            >
              <div className={styles.row}>
                <div className={styles.left}>
                  <span>
                    {statusIcon(job.status)}
                  </span>

                  <span
                    className={styles.jobName}
                  >
                    {job.job_name}
                  </span>
                </div>

                <div className={styles.right}>
                  <span
                    className={styles.duration}
                  >
                    {formatDuration(
                      job.duration_s
                    )}
                  </span>

                  {diffStr && (
                    <span className={diffColor}>
                      {diffStr}
                    </span>
                  )}
                </div>
              </div>

              <div className={styles.barBg}>
                <div
                  className={`${styles.barFill} ${barColor}`}
                  style={{
                    width: `${widthPct}%`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
import type { PipelineRun } from '../../types';
import styles from './CommitTimeline.module.css';

import { IoCheckmarkCircle, IoCloseCircle, IoRemoveCircleOutline, IoTimeOutline } from 'react-icons/io5';
import { CgSync } from 'react-icons/cg';

interface Props {
  runs: PipelineRun[];
  selectedId: number | null;
  onSelect: (run: PipelineRun) => void;
}

function statusIcon(conclusion: string | null) {
  switch (conclusion) {
    case 'success':
      return <IoCheckmarkCircle className={styles.iconGreen} />;
    case 'failure':
      return <IoCloseCircle className={styles.iconRed} />;
    case 'cancelled':
      return <IoRemoveCircleOutline className={styles.iconMuted} />;
    default:
      return <IoTimeOutline className={styles.iconMuted} />;
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

export default function CommitTimeline({runs,selectedId,onSelect,}: Props) {
  if (!runs.length) {
    return (
      <p className={styles.empty}>
        No runs synced yet. Click <CgSync className={styles.inlineIcon} /> to sync.
      </p>
    );
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>
        Recent Runs
      </h2>

      {runs.map((run) => {
        const diffPct = run.compared_to_prev_pct;

        const diffStr =
          diffPct !== null
            ? `${diffPct > 0 ? '+' : ''}${diffPct.toFixed(0)}%`
            : null;

        const diffColor =
          diffPct !== null
            ? diffPct > 20
              ? styles.diffRed
              : diffPct > 0
              ? styles.diffYellow
              : styles.diffGreen
            : '';

        return (
          <div
            key={run.id}
            className={`${styles.card} ${
              selectedId === run.id
                ? styles.selected
                : ''
            }`}
            onClick={() => onSelect(run)}
          >
            <div className={styles.row}>
              <div className={styles.left}>
                <span className={styles.icon}>
                  {statusIcon(run.conclusion)}
                </span>

                <code className={styles.hash}>
                  {run.commit_hash.slice(0, 7)}
                </code>

                {run.branch && (
                  <span className={styles.branch}>
                    {run.branch}
                  </span>
                )}
              </div>

              <div className={styles.right}>
                <span>
                  {formatDuration(
                    run.total_duration_s
                  )}
                </span>

                {diffStr && (
                  <span className={diffColor}>
                    {diffStr}
                  </span>
                )}
              </div>
            </div>

            <p className={styles.message}>
              {run.commit_message ||
                'No message'}
            </p>

            <span className={styles.time}>
              {timeAgo(run.started_at)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
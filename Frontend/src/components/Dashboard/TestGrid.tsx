import type { TestRun } from '../../types';
import styles from './TestGrid.module.css';

interface Props {
  tests: TestRun[];
  onSelect: (test: TestRun) => void;
}

function colorClass(color: string) {
  switch (color) {
    case 'green':
      return styles.green;
    case 'orange':
      return styles.orange;
    case 'red':
      return styles.red;
    default:
      return styles.default;
  }
}

function statusEmoji(color: string, status: string) {
  if (status === 'fail' || status === 'error') return '🔴';
  if (color === 'orange') return '🟠';
  if (color === 'red') return '🔴';
  return '🟢';
}

export default function TestGrid({
  tests,
  onSelect,
}: Props) {
  if (!tests.length) {
    return (
      <p className={styles.empty}>
        No test results parsed for this run.
      </p>
    );
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>
        Test Results ({tests.length})
      </h2>

      <div className={styles.grid}>
        {tests.map((test) => {
          const diffStr =
            test.diff_from_avg_pct !== null
              ? `${test.diff_from_avg_pct > 0 ? '+' : ''}${test.diff_from_avg_pct.toFixed(0)}%`
              : null;

          return (
            <div
              key={test.id}
              className={`${styles.card} ${colorClass(
                test.color
              )}`}
              onClick={() => onSelect(test)}
            >
              <div className={styles.rowTop}>
                <span>
                  {statusEmoji(
                    test.color,
                    test.status
                  )}
                </span>

                <span className={styles.name}>
                  {test.test_name}
                </span>
              </div>

              <div className={styles.rowBottom}>
                <span className={styles.muted}>
                  {test.duration_ms !== null
                    ? `${test.duration_ms}ms`
                    : '—'}
                </span>

                {diffStr && (
                  <span
                    className={
                      test.diff_from_avg_pct! > 15
                        ? styles.diffBad
                        : styles.diffGood
                    }
                  >
                    {diffStr} vs avg
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
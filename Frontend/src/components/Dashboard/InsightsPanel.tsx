import type { Insight } from '../../types';
import styles from './InsightsPanel.module.css';

interface Props {
  insights: Insight[];
}

function levelClass(level: string) {
  switch (level) {
    case 'error':
      return styles.error;
    case 'warning':
      return styles.warning;
    case 'success':
      return styles.success;
    default:
      return styles.default;
  }
}

export default function InsightsPanel({
  insights,
}: Props) {
  if (!insights.length) return null;

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>
        💡 Insights
      </h2>

      <div className={styles.list}>
        {insights.map((insight, i) => (
          <div
            key={i}
            className={`${styles.card} ${levelClass(
              insight.level
            )}`}
          >
            <div className={styles.row}>
              <span className={styles.icon}>
                {insight.icon}
              </span>

              <div className={styles.content}>
                <p className={styles.titleText}>
                  {insight.title}
                </p>

                <p className={styles.detail}>
                  {insight.detail}
                </p>

                {insight.commit_hash && (
                  <code className={styles.commit}>
                    {insight.commit_hash.slice(
                      0,
                      7
                    )}
                  </code>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
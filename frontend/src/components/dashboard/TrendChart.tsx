import { useTrends } from '../../api/hooks';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

import styles from './TrendChart.module.css';

interface Props {
  repoId: number;
}

export default function TrendChart({
  repoId,
}: Props) {
  const { data: trends, isLoading } =
    useTrends(repoId);

  if (isLoading)
    return (
      <p className={styles.loading}>
        Loading trends...
      </p>
    );

  if (!trends || !trends.length) return null;

  const data = trends.map((t) => ({
    commit: t.commit_hash.slice(0, 7),
    duration: t.total_duration_s,
    status: t.status,
    tests: t.test_count,
    passed: t.test_pass_count,
    failed: t.test_fail_count,
  }));

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>
        📈 Duration Trend
      </h2>

      <div className={styles.wrapper}>
        <ResponsiveContainer
          width="100%"
          height="100%"
        >
          <AreaChart data={data}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#374151"
            />

            <XAxis
              dataKey="commit"
              tick={{
                fontSize: 10,
                fill: '#9ca3af',
              }}
            />

            <YAxis
              tick={{
                fontSize: 10,
                fill: '#9ca3af',
              }}
              label={{
                value: 's',
                position: 'insideLeft',
                style: {
                  fontSize: 10,
                  fill: '#9ca3af',
                },
              }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid #374151',
                fontSize: 12,
              }}
              formatter={(value, name) => {
                if (name === 'duration')
                  return [`${value}s`, 'Duration'];
                return [
                  value,
                  String(name),
                ];
              }}
            />

            <Area
              type="monotone"
              dataKey="duration"
              stroke="#3b82f6"
              fill="#3b82f640"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
import { useTestHistory } from '../../api/hooks';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface Props {
  repoId: number;
  testName: string;
  onClose: () => void;
}

export default function TestDetail({ repoId, testName, onClose }: Props) {
  const { data: history, isLoading } = useTestHistory(repoId, testName);

  if (isLoading) return <p className="text-gray-400 text-sm p-4">Loading history...</p>;

  const points = (history || []).slice().reverse();
  const avgDuration = points.length
    ? points.reduce((s, p) => s + (p.duration_ms || 0), 0) / points.length
    : 0;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-200">📊 {testName}</h3>
        <button className="text-gray-400 hover:text-gray-200 text-sm" onClick={onClose}>✕</button>
      </div>

      {points.length > 0 ? (
        <>
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points}>
                <XAxis
                  dataKey="commit_hash"
                  tickFormatter={(v: string) => v.slice(0, 7)}
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  label={{ value: 'ms', position: 'insideLeft', style: { fontSize: 10, fill: '#9ca3af' } }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 12 }}
                  labelFormatter={(v) => `Commit: ${String(v).slice(0, 7)}`}
                  formatter={(v) => [`${v}ms`, 'Duration']}
                />
                <ReferenceLine y={avgDuration} stroke="#6b7280" strokeDasharray="3 3" label={{ value: 'avg', fill: '#6b7280', fontSize: 10 }} />
                <Line
                  type="monotone"
                  dataKey="duration_ms"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-medium text-gray-400 mb-1">Commit History</h4>
            {points.slice(-10).reverse().map((p, i) => {
              const icon = p.status === 'fail' || p.status === 'error' ? '🔴'
                : p.color === 'orange' ? '🟠' : '🟢';
              const diffStr = p.diff_from_avg_pct !== null
                ? `${p.diff_from_avg_pct > 0 ? '+' : ''}${p.diff_from_avg_pct.toFixed(0)}%`
                : '';
              return (
                <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-gray-700/50">
                  <div className="flex items-center gap-2">
                    <span>{icon}</span>
                    <code className="text-blue-400">{p.commit_hash.slice(0, 7)}</code>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-300">{p.duration_ms ?? '—'}ms</span>
                    {diffStr && <span className="text-gray-400">{diffStr}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <p className="text-gray-400 text-sm">No history data for this test.</p>
      )}
    </div>
  );
}

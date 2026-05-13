import type { TestRun } from '../../types';

interface Props {
  tests: TestRun[];
  onSelect: (test: TestRun) => void;
}

function colorClass(color: string) {
  switch (color) {
    case 'green': return 'bg-green-900/40 border-green-600 hover:bg-green-900/60';
    case 'orange': return 'bg-yellow-900/40 border-yellow-600 hover:bg-yellow-900/60';
    case 'red': return 'bg-red-900/40 border-red-600 hover:bg-red-900/60';
    default: return 'bg-gray-800 border-gray-600 hover:bg-gray-700';
  }
}

function statusEmoji(color: string, status: string) {
  if (status === 'fail' || status === 'error') return '🔴';
  if (color === 'orange') return '🟠';
  if (color === 'red') return '🔴';
  return '🟢';
}

export default function TestGrid({ tests, onSelect }: Props) {
  if (!tests.length) {
    return <p className="text-gray-400 text-sm">No test results parsed for this run.</p>;
  }

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 mb-2">Test Results ({tests.length})</h2>
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {tests.map((test) => {
          const diffStr = test.diff_from_avg_pct !== null
            ? `${test.diff_from_avg_pct > 0 ? '+' : ''}${test.diff_from_avg_pct.toFixed(0)}%`
            : null;
          return (
            <div
              key={test.id}
              className={`p-3 rounded border cursor-pointer transition-colors ${colorClass(test.color)}`}
              onClick={() => onSelect(test)}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span>{statusEmoji(test.color, test.status)}</span>
                <span className="text-xs font-medium text-gray-200 truncate">{test.test_name}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">
                  {test.duration_ms !== null ? `${test.duration_ms}ms` : '—'}
                </span>
                {diffStr && (
                  <span className={test.diff_from_avg_pct! > 15 ? 'text-yellow-400' : 'text-gray-400'}>
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

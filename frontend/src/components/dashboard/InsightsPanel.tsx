import type { Insight } from '../../types';

interface Props {
  insights: Insight[];
}

function levelStyle(level: string) {
  switch (level) {
    case 'error': return 'border-red-700 bg-red-900/20';
    case 'warning': return 'border-yellow-700 bg-yellow-900/20';
    case 'success': return 'border-green-700 bg-green-900/20';
    default: return 'border-blue-700 bg-blue-900/20';
  }
}

export default function InsightsPanel({ insights }: Props) {
  if (!insights.length) {
    return null;
  }

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 mb-2">💡 Insights</h2>
      <div className="space-y-2">
        {insights.map((insight, i) => (
          <div key={i} className={`p-3 rounded border ${levelStyle(insight.level)}`}>
            <div className="flex items-start gap-2">
              <span className="text-base shrink-0">{insight.icon}</span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-200">{insight.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{insight.detail}</p>
                {insight.commit_hash && (
                  <code className="text-xs text-blue-400 mt-1 inline-block">
                    {insight.commit_hash.slice(0, 7)}
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

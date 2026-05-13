interface Props {
  branch: string;
  onBranchChange: (branch: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
  branches: string[];
}

export default function Filters({ branch, onBranchChange, statusFilter, onStatusChange, branches }: Props) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-400">Branch:</label>
        <select
          className="bg-gray-800 text-gray-200 text-xs rounded px-2 py-1 border border-gray-600"
          value={branch}
          onChange={(e) => onBranchChange(e.target.value)}
        >
          <option value="">All</option>
          {branches.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-400">Status:</label>
        <select
          className="bg-gray-800 text-gray-200 text-xs rounded px-2 py-1 border border-gray-600"
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
        >
          <option value="">All</option>
          <option value="success">✅ Success</option>
          <option value="failure">❌ Failure</option>
          <option value="cancelled">⚪ Cancelled</option>
        </select>
      </div>
    </div>
  );
}

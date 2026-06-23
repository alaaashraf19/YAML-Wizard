interface Props {
  branch: string;
  onBranchChange: (branch: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
  branches: string[];
}

import styles from './Filters.module.css';

export default function Filters({
  branch,
  onBranchChange,
  statusFilter,
  onStatusChange,
  branches,
}: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.group}>
        <label className={styles.label}>
          Branch:
        </label>

        <select
          className={styles.select}
          value={branch}
          onChange={(e) =>
            onBranchChange(e.target.value)
          }
        >
          <option value="">All</option>

          {branches.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.group}>
        <label className={styles.label}>
          Status:
        </label>

        <select
          className={styles.select}
          value={statusFilter}
          onChange={(e) =>
            onStatusChange(e.target.value)
          }
        >
          <option value="">All</option>
          <option value="success">
            ✅ Success
          </option>
          <option value="failure">
            ❌ Failure
          </option>
          <option value="cancelled">
            ⚪ Cancelled
          </option>
        </select>
      </div>
    </div>
  );
}
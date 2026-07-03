import { useEffect, useRef, useState } from 'react';
import gStyles from '../../global.module.css';
import styles from './Filters.module.css';

import { FiFilter } from 'react-icons/fi';
import { IoClose, IoCheckmarkCircle, IoCloseCircle, IoRemoveCircleOutline } from 'react-icons/io5';

interface Props {
  branch: string;
  onBranchChange: (branch: string) => void;
  statusFilter: string;
  onStatusChange: (status: string) => void;
  branches: string[];
}

const STATUS_OPTIONS: { value: string; label: string; icon: React.ReactNode }[] = [
  { value: 'success', label: 'Success', icon: <IoCheckmarkCircle className={styles.optionIcon} /> },
  { value: 'failure', label: 'Failure', icon: <IoCloseCircle className={styles.optionIcon} /> },
  { value: 'cancelled', label: 'Cancelled', icon: <IoRemoveCircleOutline className={styles.optionIcon} /> },
];

export default function Filters({
  branch,
  onBranchChange,
  statusFilter,
  onStatusChange,
  branches,
}: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const activeCount = (branch ? 1 : 0) + (statusFilter ? 1 : 0);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={styles.container} ref={menuRef}>
      <button
        className={`${styles.filterTrigger} ${gStyles.clickable} ${
          activeCount > 0 ? styles.filterTriggerActive : ''
        }`}
        onClick={() => setOpen((prev) => !prev)}
      >
        <FiFilter className={styles.triggerIcon} />
        Filters
        {activeCount > 0 && (
          <span className={styles.activeBadge}>{activeCount}</span>
        )}
      </button>

      {open && (
        <div className={styles.filterMenu}>
          <div className={styles.filterHeader}>
            <span>Branch</span>

            {branch && (
              <IoClose
                className={`${styles.removeFilter} ${gStyles.clickable}`}
                onClick={() => onBranchChange('')}
                title="Clear branch filter"
              />
            )}
          </div>

          <div className={styles.options}>
            {branches.length === 0 && (
              <span className={styles.noOptions}>No branches yet</span>
            )}

            {branches.map((b) => (
              <span
                key={b}
                className={`${styles.option} ${gStyles.clickable} ${
                  branch === b ? styles.selected : styles.notSelected
                }`}
                onClick={() =>
                  onBranchChange(branch === b ? '' : b)
                }
              >
                {b}
              </span>
            ))}
          </div>

          <div className={styles.divider} />

          <div className={styles.filterHeader}>
            <span>Status</span>

            {statusFilter && (
              <IoClose
                className={`${styles.removeFilter} ${gStyles.clickable}`}
                onClick={() => onStatusChange('')}
                title="Clear status filter"
              />
            )}
          </div>

          <div className={styles.options}>
            {STATUS_OPTIONS.map((opt) => (
              <span
                key={opt.value}
                className={`${styles.option} ${gStyles.clickable} ${
                  statusFilter === opt.value ? styles.selected : styles.notSelected
                }`}
                onClick={() =>
                  onStatusChange(statusFilter === opt.value ? '' : opt.value)
                }
              >
                {opt.icon}
                {opt.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
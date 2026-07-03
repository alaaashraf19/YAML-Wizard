import { useMemo, useState } from 'react';
import type { TestRun } from '../../types';
import styles from './TestGrid.module.css';

import { FiSearch } from 'react-icons/fi';
import { IoClose, IoEllipseSharp } from 'react-icons/io5';

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

function statusDotClass(color: string, status: string) {
  if (status === 'fail' || status === 'error') return styles.dotRed;
  if (color === 'orange') return styles.dotOrange;
  if (color === 'red') return styles.dotRed;
  return styles.dotGreen;
}

export default function TestGrid({
  tests,
  onSelect,
}: Props) {
  const [query, setQuery] = useState('');

  const filteredTests = useMemo(() => {
    if (!query.trim()) return tests;
    const q = query.trim().toLowerCase();
    return tests.filter((t) => t.test_name.toLowerCase().includes(q));
  }, [tests, query]);

  if (!tests.length) {
    return (
      <p className={styles.empty}>
        No test results parsed for this run.
      </p>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          Test Results ({filteredTests.length}/{tests.length})
        </h2>

        <div className={styles.searchRow}>
          <FiSearch className={styles.searchIcon} />

          <input
            className={styles.searchInput}
            placeholder="Search tests..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          {query && (
            <IoClose
              className={styles.clearIcon}
              onClick={() => setQuery('')}
              title="Clear search"
            />
          )}
        </div>
      </div>

      {filteredTests.length === 0 && (
        <p className={styles.empty}>No tests match "{query}".</p>
      )}

      <div className={styles.grid}>
        {filteredTests.map((test) => {
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
                <IoEllipseSharp
                  className={`${styles.statusDot} ${statusDotClass(
                    test.color,
                    test.status
                  )}`}
                />

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
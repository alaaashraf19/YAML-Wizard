import { useEffect, useRef } from 'react';
import { BiMessageSquareError, BiX, BiCheckCircle, BiInfoCircle } from 'react-icons/bi';
import { FiAlertTriangle } from 'react-icons/fi';
import styles from './PipelineReview.module.css';
import { useHistoryStore } from '../../pages/History';

interface ReviewProps {
  review: any;
  isReviewOpen: boolean;
  setIsReviewOpen: (isOpen: boolean) => void;
  handleSubmit: () => void;
}

export default function PipelineReview({ review, isReviewOpen, setIsReviewOpen, handleSubmit }: ReviewProps) {
    const { pipeline } = useHistoryStore();
  const popupRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isReviewOpen && 
          popupRef.current && 
          buttonRef.current && 
          !popupRef.current.contains(event.target as Node) && 
          !buttonRef.current.contains(event.target as Node)) {
        setIsReviewOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isReviewOpen, setIsReviewOpen]);

  const hasErrors = review.errors?.length > 0;
  const hasWarnings = review.warnings?.length > 0 || review.ai_warnings?.length > 0;
  const totalWarnings = (review.warnings?.length || 0) + (review.ai_warnings?.length || 0);
  const totalErrors = review.errors?.length || 0;

  const getWarningIcon = (level: string) => {
    if (level === 'error') return <BiX className={styles.errorIcon} />;
    if (level === 'warning') return <FiAlertTriangle className={styles.warningIcon} />;
    return <BiInfoCircle className={styles.infoIcon} />;
  };

  return (
    <div className={styles.container}>
      <button 
        ref={buttonRef}
        className={`${styles.logsBtn} ${hasWarnings || hasErrors ? styles.hasWarnings : ''}`}
        onClick={() => setIsReviewOpen(!isReviewOpen)}
      >
        <span className={styles.btnText}>
          {hasErrors ? `${totalErrors} Errors` : hasWarnings ? `${totalWarnings} Warnings` : 'Review'}
        </span>
        <BiMessageSquareError />
        {(hasWarnings || hasErrors) && (
          <span className={`${styles.warningBadge} ${hasErrors ? styles.errorBadge : ''}`}>
            {hasErrors ? totalErrors : totalWarnings}
          </span>
        )}
      </button>

      {isReviewOpen && (
        <div 
          ref={popupRef}
          className={styles.popupOverlay}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={styles.popupContent}>
            {/* Header */}
            <div className={styles.popupHeader}>
              <h2 className={styles.popupTitle}>Pipeline Review</h2>
              <button className={styles.closeBtn} onClick={() => setIsReviewOpen(false)}>
                <BiX />
              </button>
            </div>

            {/* AI Review Status */}
            <div className={styles.section}>
              <div className={styles.aiStatus}>
                <span className={styles.aiLabel}>AI Review:</span>
                {review.ai_review?.available ? (
                  <span className={styles.success}><BiCheckCircle /> Available</span>
                ) : (
                  <span className={styles.error}><BiX /> Unavailable</span>
                )}
                {review.ai_review?.model && (
                  <span className={styles.model}>({review.ai_review.model})</span>
                )}
                {review.ai_review?.error && (
                  <span className={styles.aiError}>({review.ai_review.error})</span>
                )}
              </div>
            </div>

            {/* Quick Info */}
            <div className={styles.quickInfo}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Platform</span>
                <span className={styles.infoValue}>{review.platform || 'N/A'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Author</span>
                <span className={styles.infoValue}>{pipeline?.commit_author || 'N/A'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Branch</span>
                <span className={styles.infoValue}>{pipeline?.branch || 'N/A'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Jobs</span>
                <span className={styles.infoValue}>{review.jobs?.length || 0}</span>
              </div>
            </div>

            {/* Errors Section */}
            {hasErrors && (
              <div className={styles.errorsContainer}>
                <h3 className={styles.errorsTitle}>
                  <BiX className={styles.errorIconLarge} />
                  Errors ({totalErrors}) - Cannot Submit
                </h3>
                {review.errors?.map((error: any, index: number) => (
                  <div key={`e-${index}`} className={styles.errorItem}>
                    <div className={styles.errorHeader}>
                      <BiX className={styles.errorIcon} />
                      <span className={styles.errorTitle}>{error.title || 'Error'}</span>
                    </div>
                    {error.message && (
                      <p className={styles.errorMsg}>{error.message}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Warnings */}
            <div className={styles.warningsContainer}>
              {totalWarnings > 0 ? (
                <>
                  <h3 className={styles.warningsTitle}>Warnings ({totalWarnings})</h3>
                  
                  {/* Regular Warnings */}
                  {review.warnings?.map((warning: any, index: number) => (
                    <div key={`w-${index}`} className={styles.warningItem}>
                      <div className={styles.warningHeader}>
                        {getWarningIcon(warning.level)}
                        <span className={styles.warningTitle}>{warning.title || 'Warning'}</span>
                      </div>
                      {warning.message && (
                        <p className={styles.warningMsg}>{warning.message}</p>
                      )}
                    </div>
                  ))}

                  {/* AI Warnings */}
                  {review.ai_warnings?.map((warning: any, index: number) => (
                    <div key={`ai-${index}`} className={`${styles.warningItem} ${styles.aiWarning}`}>
                      <div className={styles.warningHeader}>
                        {getWarningIcon(warning.level)}
                        <span className={styles.warningTitle}>{warning.title}</span>
                        <span className={styles.category}>{warning.category}</span>
                        {warning.job && <span className={styles.jobTag}>Job: {warning.job}</span>}
                      </div>
                      <p className={styles.warningMsg}>{warning.message}</p>
                      {warning.suggestion && (
                        <div className={styles.suggestion}>
                          <span className={styles.suggestionLabel}>Suggestion:</span>
                          <span>{warning.suggestion}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </>
              ) : !hasErrors && (
                <div className={styles.noWarnings}>
                  <BiCheckCircle className={styles.successIcon} />
                  <span>All good! No warnings or errors found.</span>
                </div>
              )}
            </div>

            <div className={styles.actions}>
              <button 
                className={`${styles.submitBtn} ${hasErrors ? styles.submitDisabled : ''}`}
                onClick={handleSubmit}
                disabled={hasErrors}
                title={hasErrors ? 'Cannot submit - pipeline has errors' : 'Submit pipeline'}
              >
                {hasErrors ? 'Cannot Submit - Fix Errors First' : 'Submit Pipeline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
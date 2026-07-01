import { useEffect, useState } from "react";
import styles from "./ProjectLoadingIndicator.module.css";

// cycling status messages so the wait for repo-context fetching feels
// purposeful instead of a frozen screen
const STAGES = [
    "Connecting to repository...",
    "Fetching repository context...",
    "Analyzing project structure...",
    "Almost done...",
];

function ProjectLoadingIndicator() {
    const [stageIndex, setStageIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setStageIndex((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev));
        }, 1800);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className={styles.wrapper}>
            <div className={styles.spinner}>
                <div className={styles.ring} />
            </div>
            <span key={stageIndex} className={styles.stageText}>{STAGES[stageIndex]}</span>
        </div>
    );
}

export default ProjectLoadingIndicator;

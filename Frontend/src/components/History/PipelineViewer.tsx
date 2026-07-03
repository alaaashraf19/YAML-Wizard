import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'
import ChatbotBubble from './ChatbotBubble';
import type { Job } from '../../types';
import { useHistoryStore } from "../../pages/History";
import { useRef, useState } from 'react';

import { MdEdit } from "react-icons/md";
import { MdBrightness6 } from "react-icons/md";
import { MdBrightness2 } from "react-icons/md";
import { BiTestTube } from "react-icons/bi";
import { CgFileDocument } from "react-icons/cg";
import { FaCheckCircle, FaTimesCircle, FaClock, FaExternalLinkAlt } from "react-icons/fa";
import { BiX } from "react-icons/bi";

import {create} from "zustand";
import {persist,createJSONStorage} from "zustand/middleware";
import Popup from "../Popup/Popup";

type ViewerProps = {
    jobs: Job[]
}

type TestResult = {
    id?: number,
    pipeline_id: number,
    project_id?: number,
    platform: string,
    status: string,
    valid: boolean,
    external_pipeline_id: number,
    ref: string,
    web_url: string,
    duration_s: number,
    jobs: [
      {
        name: string,
        stage: string,
        status: string,
        duration_s: number,
        allow_failure: boolean,
        web_url: string
      }
    ],
    cleaned_up: false,
    message: string,
    created_at?: Date
  }

type ViewerStore = {
    isTestRunning: boolean,
    setIsTestRunning: (isTestRunning :boolean) => void,

    result: TestResult | null,
    setResult: (result: TestResult | null) => void,

    testHistory: TestResult[],
    setTestHistory: (testHistory: TestResult[]) => void,
}

export const useViewerStore = create<ViewerStore>()(
    persist((set)=> ({
        isTestRunning: false,
        setIsTestRunning: isTestRunning => set({isTestRunning}),

        result: null,
        setResult: result => set({result}),

        testHistory: [],
        setTestHistory: testHistory => set({testHistory})
    }),{
        name: "history_store",
        storage: createJSONStorage(() => sessionStorage)
    })
);

function PipelineViewer({ jobs }:ViewerProps){
    const {project, pipeline, isDark, setIsDark, setIsEdit} = useHistoryStore();

    const {isTestRunning, setIsTestRunning, result, setResult} = useViewerStore();

    const [isChatOpen, setIsChatOpen] = useState(false);
    const [isResultOpen, setIsResultOpen] = useState(false);
    const [confirmDryrun, setConfirmDryrun] = useState<string | null>("");
    const [errorDryrun, setErrorDryrun] = useState<string | null>("");

    const popupRef = useRef<HTMLDivElement>(null);
    const resultPopupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;

    const startDryRun = async () => {
        if(!project || !pipeline) return;

        setIsTestRunning(true);

        try{
            const res = await fetch(`${api_url}/dry-run/${project.platform}/${project.id}/${pipeline.id}`, {
                method: "POST",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.detail?.[0]?.msg || data.detail || "Failed to test this pipeline using dry-run";
                console.error(errorMsg);
                setErrorDryrun(errorMsg);
                setIsTestRunning(false);
                return;
            }

            setIsTestRunning(false);
            setResult(data);
            setIsResultOpen(true);

            setConfirmDryrun(`Dry-run testing of pipeline ${pipeline.name} has completed.\n
                close this and see "Test Result" to see the results`);

        } catch (e) {
            const errorMsg = "Failed to delete publish:";
            console.error(errorMsg, e);
            setErrorDryrun(errorMsg);
            setIsTestRunning(false);
        }
    }

    const getStatusIcon = (status: string) => {
        if (status === 'success' || status === 'passed') {
            return <FaCheckCircle className={styles.statusSuccess} />;
        } else if (status === 'failed' || status === 'error') {
            return <FaTimesCircle className={styles.statusFailed} />;
        } else {
            return <FaClock className={styles.statusPending} />;
        }
    };

    const getStatusColor = (status: string) => {
        if (status === 'success' || status === 'passed') return styles.statusSuccess;
        if (status === 'failed' || status === 'error') return styles.statusFailed;
        return styles.statusPending;
    };

    let lineNumber = 1;
    return(
        <div className={`${styles.pipeline} ${isDark? styles.dark : styles.bright}`}>
            <div className={styles.btnsContainer}>

                <button className={`${styles.testBtn} ${gStyles.clickable}`}
                    onClick={startDryRun} disabled={isTestRunning}>
                    <BiTestTube/>
                    <span className={styles.btnText}>
                        {isTestRunning ? "Testing..." : "Start dry-run"}
                    </span>
                </button>

                {result && (
                    <button 
                        className={`${styles.testBtn} ${gStyles.clickable}`}
                        onClick={() => setIsResultOpen(true)}
                    >
                        <CgFileDocument/>
                        <span className={styles.btnText}>Test Result</span>
                    </button>
                )}

                <MdEdit className={`${styles.editBtn} ${gStyles.clickable}`} 
                    title="Open Editor" onClick={() => setIsEdit(true)}/>
            </div>

            {jobs.map((job, jobIndex) => {
                let lines = job.content.split("\n");
                let startLine = lineNumber;
                lineNumber += lines.length;
                return(
                    <div key={jobIndex} className={styles.job}>
                        {lines.map((line, index) => {
                            const currentLine=startLine++;
                            return(
                            <div key={index} className={styles.yamlLine}>
                                <span className={styles.lineNumber}>
                                    {currentLine}
                                </span>
                                <span className={styles.lineText}>{line}</span>
                            </div>
                        );})}
                    </div>
                );
            })}

            <div className={`${styles.themeBtn} ${isDark ? styles.dark : ""}`}
                onClick={()=>setIsDark(!isDark)} title="Change Theme">
                <MdBrightness6 className={styles.sunIcon}/>
                <MdBrightness2 className={styles.moonIcon}/>
            </div>
            <ChatbotBubble
                isChatOpen={isChatOpen}
                setIsChatOpen={setIsChatOpen}
            />

            {(confirmDryrun || errorDryrun) && 
                <Popup
                btnText1="Got it"
                confirmMessage={confirmDryrun}
                setConfirmMessage={setConfirmDryrun}
                errorMessage={errorDryrun}
                setErrorMessage={setErrorDryrun}
                popupRef={popupRef}
            />}

            {/* Test Results Popup */}
            {isResultOpen && result && (
                <div 
                    ref={resultPopupRef}
                    className={styles.resultOverlay}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className={styles.resultContent}>
                        <div className={styles.resultHeader}>
                            <h2>Test Results</h2>
                            <button 
                                className={styles.closeBtn}
                                onClick={() => setIsResultOpen(false)}
                            >
                                <BiX />
                            </button>
                        </div>

                        {/* Overall Status */}
                        <div className={styles.resultStatus}>
                            <div className={styles.statusBadge}>
                                {getStatusIcon(result.status)}
                                <span className={getStatusColor(result.status)}>
                                    {result.status.toUpperCase()}
                                </span>
                            </div>
                            {result.valid && (
                                <span className={styles.validBadge}>
                                    <FaCheckCircle /> Valid
                                </span>
                            )}
                        </div>

                        {/* Quick Info */}
                        <div className={styles.resultInfo}>
                            <div className={styles.infoRow}>
                                <span className={styles.infoLabel}>Platform</span>
                                <span>{result.platform}</span>
                            </div>
                            <div className={styles.infoRow}>
                                <span className={styles.infoLabel}>Duration</span>
                                <span>{result.duration_s}s</span>
                            </div>
                            <div className={styles.infoRow}>
                                <span className={styles.infoLabel}>Ref</span>
                                <span>{result.ref}</span>
                            </div>
                            <div className={styles.infoRow}>
                                <span className={styles.infoLabel}>Message</span>
                                <span className={styles.messageText}>{result.message || 'N/A'}</span>
                            </div>
                            {result.web_url && (
                                <div className={styles.infoRow}>
                                    <span className={styles.infoLabel}>Web URL</span>
                                    <a href={result.web_url} target="_blank" rel="noopener noreferrer" 
                                       className={styles.webLink}>
                                        View Pipeline <FaExternalLinkAlt className={styles.externalIcon} />
                                    </a>
                                </div>
                            )}
                        </div>

                        {/* Jobs */}
                        {result.jobs && result.jobs.length > 0 && (
                            <div className={styles.jobsSection}>
                                <h3>Jobs ({result.jobs.length})</h3>
                                <div className={styles.jobsList}>
                                    {result.jobs.map((job, index) => (
                                        <div key={index} className={styles.jobResult}>
                                            <div className={styles.jobHeader}>
                                                <div className={styles.jobName}>
                                                    {getStatusIcon(job.status)}
                                                    <span>{job.name}</span>
                                                </div>
                                                <div className={styles.jobMeta}>
                                                    <span className={styles.jobStage}>{job.stage}</span>
                                                    <span className={styles.jobDuration}>{job.duration_s}s</span>
                                                    {job.allow_failure && (
                                                        <span className={styles.allowFailure}>Allow Failure</span>
                                                    )}
                                                </div>
                                            </div>
                                            <div className={styles.jobStatus}>
                                                <span className={getStatusColor(job.status)}>
                                                    {job.status}
                                                </span>
                                                {job.web_url && (
                                                    <a href={job.web_url} target="_blank" rel="noopener noreferrer"
                                                       className={styles.jobLink}>
                                                        View Job
                                                    </a>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default PipelineViewer;
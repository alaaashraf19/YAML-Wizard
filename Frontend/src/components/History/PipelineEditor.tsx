import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'

import ChatbotBubble from "./ChatbotBubble";
import SortableJob from './SortableJob';
import type { Job, JobReview } from "../../types";
import { useEffect, useRef, useState, useCallback } from "react";

import { FaCircleCheck } from "react-icons/fa6";
import { IoClose } from "react-icons/io5";
import { MdBrightness6, MdBrightness2 } from "react-icons/md";
import { MdFactCheck } from "react-icons/md";

import { DndContext, type DragEndEvent } from "@dnd-kit/core";
import { arrayMove, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

import { useHistoryStore } from "../../pages/History";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import Popup from "../Popup/Popup";
import PipelineReview from "./PipelineReview";


type EditorProps = {
    initJobs: Job[],
    setInitJobs: React.Dispatch<React.SetStateAction<Job[]>>,
    isDiscardChanges: boolean,
    setDiscardChanges: React.Dispatch<React.SetStateAction<boolean>>,
}

type HistoryEntry = {
    jobs: Job[];
    type: 'structural' | 'tab' | 'text';
    tabInfo?: {
        jobIndex: number;
        start: number;
        end: number;
        textBefore: string;
        textAfter: string;
    };
    textInfo?: {
        jobIndex: number;
        content: string;
    };
};

type HistoryState = {
    snapshots: HistoryEntry[];
    index: number;
};

type EditorStore = {
    pipelineId: number | null,

    jobs: Job[],
    setJobs: (jobs: Job[]) => void,
    
    history: HistoryState,
    setHistory: (history: HistoryState) => void,

    review: JobReview | null,
    setReview: (review: JobReview | null) => void,

    originalJobs: Job[],
    setOriginalJobs: (jobs: Job[]) => void,

    hasChanges: boolean;
    setHasChanges: (hasChanges: boolean) => void,

    resetEditorState: (newJobs: Job[], pipelineId: number | null) => void
}

export const useEditorStore = create<EditorStore>()(
    persist(
        (set) => ({
            pipelineId: null,
            jobs: [],
            setJobs: (jobs) => set({ jobs }),
            
            history: { snapshots: [], index: 0 },
            setHistory: (history) => set({ history }),

            review: null,
            setReview: (review) => set({review}),

            originalJobs: [],
            setOriginalJobs: (jobs) => set({ originalJobs: jobs }),

            hasChanges: false,
            setHasChanges: (hasChanges) => set({ hasChanges }),

            resetEditorState: (newJobs: Job[], pipelineId: number | null) => {
                const initialSnapshot: HistoryEntry = {
                    jobs: structuredClone(newJobs),
                    type: 'structural'
                };
                
                set({
                    pipelineId,
                    jobs: structuredClone(newJobs),
                    originalJobs: structuredClone(newJobs),
                    history: {
                        snapshots: [initialSnapshot],
                        index: 0,
                    },
                    hasChanges: false,
                    review: null,
                });
            },

        }),
        {
            name: "editor_store",
            storage: createJSONStorage(() => sessionStorage),
            partialize: (state) => ({
                pipelineId: state.pipelineId,
                history: state.history,
                jobs: state.jobs,
                hasChanges: state.hasChanges,
                review: state.review,
            }),
        }
    )
);

function PipelineEditor({ initJobs, isDiscardChanges, setDiscardChanges, setInitJobs }: EditorProps) {
    const MAX_SNAPSHOTS = 50;
    const {isDark, setIsDark, setIsEdit, project, pipeline, setPipeline} = useHistoryStore();

    const {jobs, setJobs, history, setHistory, hasChanges, setHasChanges,
        resetEditorState, review, setReview, pipelineId} = useEditorStore();

    const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
    const [isReviewOpen, setIsReviewOpen] = useState<boolean>(false);
    const [isReviewing, setIsReviewing] = useState<boolean>(false);

    const [askDiscard, setAskDiscard] = useState<string | null>(null);
    const [warningDiscard, setWarningDiscard] = useState<string | null>(null);
    const [askSubmit, setAskSubmit] = useState<string | null>(null);
    const [confirmSubmit, setConfirmSubmit] = useState<string | null>(null);
    const [warningSubmit, setWarningSubmit] = useState<string | null>(null);
    const [errorSubmit, setErrorSubmit] = useState<string | null>(null);

    const jobsEndRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement>(null);

    const api_url = import.meta.env.VITE_API_URL;

    const isRestoringFromHistory = useRef(false);
    const isUndoRedoInProgress = useRef(false);
    const currentPipelineIdRef = useRef<number | null>(null);
    const originalJobsRef = useRef<Job[]>([]);

    // Update originalJobsRef when initJobs changes
    useEffect(() => {
        if (initJobs.length > 0) {
            originalJobsRef.current = structuredClone(initJobs);
            console.log("Initialized original jobs");
        }
    }, [initJobs]);

    // handle pipeline changes with first load support
    useEffect(() => {
        const currentPipelineId = pipeline?.id || null;
        if (!pipeline || initJobs.length === 0) {
            if (currentPipelineIdRef.current !== null) {
                console.log("No pipeline selected or jobs empty. Closing editor.");
                currentPipelineIdRef.current = null;
                setIsEdit(false);
            }
            return;
        }

        if (pipelineId !== currentPipelineId) {
            console.log(`Pipeline changed from ${pipelineId} to ${currentPipelineId}. Resetting state.`);
            
            originalJobsRef.current = structuredClone(initJobs);
            currentPipelineIdRef.current = currentPipelineId;
            
            resetEditorState(initJobs, currentPipelineId);
        } else {
            currentPipelineIdRef.current = currentPipelineId;
            if (originalJobsRef.current.length === 0) {
                originalJobsRef.current = structuredClone(initJobs);
            }
        }
        
    }, [initJobs, pipeline, pipelineId, resetEditorState, setIsEdit]);

    //Handle discard changes
    useEffect(() => {
        if (isDiscardChanges) {
            console.log("Discarding changes - resetting to original jobs");
            
            const originalJobs = originalJobsRef.current;
            const currentPipelineId = pipeline?.id || null;
            
            if (originalJobs.length > 0) {
                resetEditorState(originalJobs, currentPipelineId);
                setInitJobs(originalJobs);
            }
            
            setIsEdit(false);
            setDiscardChanges(false);
            setReview(null);
        }
    }, [isDiscardChanges, resetEditorState, setIsEdit, setDiscardChanges, setReview, setInitJobs, pipeline?.id]);
    
    const getStorageSize = () => {
        let total = 0;
        for (let key in sessionStorage) {
            if (sessionStorage.hasOwnProperty(key)) {
                total += sessionStorage[key].length * 2;
            }
        }
        return total / (1024 * 1024);
    };

    const saveHistory = useCallback((jobs: Job[], type: HistoryEntry['type'], extraInfo?: any) => {
        const snapshot = structuredClone(jobs);
        let snapshots = history.snapshots.slice(0, history.index + 1);
        const entry: HistoryEntry = { jobs: snapshot, type };
        
        if (type === 'tab' && extraInfo) {
            entry.tabInfo = extraInfo;
        } else if (type === 'text' && extraInfo) {
            entry.textInfo = extraInfo;
        }
        
        snapshots.push(entry);

        if (snapshots.length > MAX_SNAPSHOTS) {
            const excess = snapshots.length - MAX_SNAPSHOTS;
            snapshots = snapshots.slice(excess);

            const newIndex = Math.max(0, history.index - excess);
            const finalIndex = Math.min(newIndex, snapshots.length - 1);
            setHistory({ snapshots, index: finalIndex });
        } else {
            if (getStorageSize() > 4.5) {
                console.warn('Session storage approaching limit');
                snapshots = snapshots.slice(-30);
            }
            setHistory({ snapshots, index: snapshots.length - 1 });
        }
        
        setHasChanges(true);
    }, [history, setHistory, setHasChanges]);

    const saveStructuralChange = useCallback((newJobs: Job[]) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'structural');
    }, [saveHistory, setJobs]);

    const saveTabChange = useCallback((newJobs: Job[], jobIndex: number, start: number, end: number, textBefore: string, textAfter: string) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'tab', { jobIndex, start, end, textBefore, textAfter });
    }, [saveHistory, setJobs]);

    const saveTextChange = useCallback((newJobs: Job[], jobIndex: number, content: string) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'text', { jobIndex, content });
    }, [saveHistory, setJobs]);

    const updateJobContent = useCallback((jobIndex: number, content: string) => {
        if (isRestoringFromHistory.current) return;
        
        const newJobs = structuredClone(jobs);
        newJobs[jobIndex] = { ...newJobs[jobIndex], content };
        saveTextChange(newJobs, jobIndex, content);
    }, [jobs, saveTextChange]);

    const undo = useCallback(() => {
        if (isUndoRedoInProgress.current) return;
        if (history.index <= 0) return;
        
        const currentEntry = history.snapshots[history.index];
        const previousEntry = history.snapshots[history.index - 1];
        const nextIndex = history.index - 1;
        
        isUndoRedoInProgress.current = true;
        isRestoringFromHistory.current = true;
        
        if (currentEntry.type === 'tab' && currentEntry.tabInfo) {
            const textarea = document.querySelector(
                `textarea[data-job-index="${currentEntry.tabInfo.jobIndex}"]`
            ) as HTMLTextAreaElement;
            
            if (textarea) {
                textarea.value = currentEntry.tabInfo.textBefore;
                const event = new Event('input', { bubbles: true });
                textarea.dispatchEvent(event);
                
                requestAnimationFrame(() => {
                    textarea.setSelectionRange(currentEntry.tabInfo!.start, currentEntry.tabInfo!.start);
                    textarea.focus();
                });
            }
        }
        
        setJobs(structuredClone(previousEntry.jobs));
        setHistory({...history, index: nextIndex});
        
        setTimeout(() => {
            isRestoringFromHistory.current = false;
            isUndoRedoInProgress.current = false;
        }, 50);
    }, [history, setJobs, setHistory]);

    const redo = useCallback(() => {
        if (isUndoRedoInProgress.current) return;
        if (history.index >= history.snapshots.length - 1) return;
        
        const nextEntry = history.snapshots[history.index + 1];
        const nextIndex = history.index + 1;
        
        isUndoRedoInProgress.current = true;
        isRestoringFromHistory.current = true;
        
        if (nextEntry.type === 'tab' && nextEntry.tabInfo) {
            const textarea = document.querySelector(
                `textarea[data-job-index="${nextEntry.tabInfo.jobIndex}"]`
            ) as HTMLTextAreaElement;
            
            if (textarea) {
                textarea.value = nextEntry.tabInfo.textAfter;
                const event = new Event('input', { bubbles: true });
                textarea.dispatchEvent(event);
                
                requestAnimationFrame(() => {
                    textarea.setSelectionRange(nextEntry.tabInfo!.start + 2, nextEntry.tabInfo!.start + 2);
                    textarea.focus();
                });
            }
        }
        
        setJobs(structuredClone(nextEntry.jobs));
        setHistory({...history, index: nextIndex});
        
        setTimeout(() => {
            isRestoringFromHistory.current = false;
            isUndoRedoInProgress.current = false;
        }, 50);
    }, [history, setJobs, setHistory]);

    const handleTabKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>, jobIndex: number) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const textarea = e.currentTarget;
            const { selectionStart, selectionEnd, value } = textarea;
            const tab = "  ";
            
            const textBefore = value;
            const newValue = value.slice(0, selectionStart) + tab + value.slice(selectionEnd);
            const textAfter = newValue;
            
            const newJobs = structuredClone(jobs);
            newJobs[jobIndex] = { ...newJobs[jobIndex], content: newValue };
            
            saveTabChange(newJobs, jobIndex, selectionStart, selectionEnd, textBefore, textAfter);
            
            requestAnimationFrame(() => {
                textarea.setSelectionRange(selectionStart + tab.length, selectionStart + tab.length);
            });
        }
    }, [jobs, saveTabChange]);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (isUndoRedoInProgress.current) return;
            if (!(e.ctrlKey || e.metaKey)) return;

            if (e.key.toLowerCase() === "z") {
                e.preventDefault();
                undo();
                return;
            }
            
            if (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey)) {
                e.preventDefault();
                redo();
                return;
            }
        };
        
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [undo, redo]);

    const moveJob = useCallback((index: number, direction: -1 | 1) => {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= jobs.length) return;

        const copy = [...jobs];
        [copy[index], copy[newIndex]] = [copy[newIndex], copy[index]];

        saveStructuralChange(copy);
    }, [jobs, saveStructuralChange]);

    const addJob = useCallback(() => {
        const newJobs = [...jobs, {
            id: "new_job",
            content: "new_job:\n  stage:\n  script:"
        }];
        saveStructuralChange(newJobs);
    }, [jobs, saveStructuralChange]);

    const deleteJob = useCallback((jobIndex: number) => {
        if (jobs.length === 1) return;
        
        const copy = [...jobs];
        copy.splice(jobIndex, 1);
        saveStructuralChange(copy);
    }, [jobs, saveStructuralChange]);

    const handleDragEnd = useCallback(({ active, over }: DragEndEvent) => {
        if (!over || active.id === over.id) return;
        
        const oldIndex = jobs.findIndex(j => j.id === active.id);
        const newIndex = jobs.findIndex(j => j.id === over.id);
        const newJobs = arrayMove(jobs, oldIndex, newIndex);
        
        saveStructuralChange(newJobs);
    }, [jobs, saveStructuralChange]);

    const reviewJobs = async ()=> {
        if(!project || !pipeline)return;
        setIsReviewing(true);
        try {
            const res = await fetch(`${api_url}/projects/${project.id}/pipelines/${pipeline.id}/jobs`, {
                credentials: "include",
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    jobs: jobs.map(job => ({
                        id: job.id,
                        content: job.content
                    }))
                })
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipeline script");
                setErrorSubmit("Something went wrong while reviewing the pipeline script. Please try again later.");
                setIsReviewing(false);
                return;
            }
            setReview(data);
            setIsReviewing(false);

        }catch(e: any){
            console.error(`Failed to get jobs of pipeline with id: ${pipeline.id}`)
            setIsReviewing(false);
        }
    };

    const submitJobs = async ()=> {
        if(!project || !pipeline)return;
        try {
            const res = await fetch(`${api_url}/projects/${project.id}/pipelines/${pipeline.id}/jobs/commit`, {
                credentials: "include",
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    jobs: jobs.map(job => ({
                        id: job.id,
                        content: job.content
                    }))
                })
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to submit changes");
                return;
            }
            // setInitJobs(jobs);
            setConfirmSubmit("Submitted successfully, You can find the new version in history version");
            setPipeline(pipeline && {...pipeline, updated_at:new Date()});
            setDiscardChanges(true);

        }catch(e: any){
            console.error(`Failed to submit changes of pipeline with id: ${pipeline.id}`)
        }
    };

    const handleSubmit = () => {
        setAskSubmit(`Save changes to history${(review?.ai_warnings || review?.warnings) ? " with errors/warnings" : ""} ?`),
        setWarningSubmit("Open the logs to review the errors/warnings before saving.")
    }

    let lineNumber = 1;
    return (
        <DndContext onDragEnd={handleDragEnd}>
            <SortableContext items={jobs.map(j => j.id)} strategy={verticalListSortingStrategy}>
                <div className={`${styles.pipeline} ${isDark ? styles.dark : styles.bright}`}>
                    <div className={styles.btnsContainer}>
 
                        <button className={`${styles.addBtn} ${gStyles.clickable}`}
                            onClick={() => {
                                addJob();
                                requestAnimationFrame(() => {
                                    jobsEndRef.current?.scrollIntoView({ behavior: "smooth" });
                                });
                            }}> Add Job </button>

                        {review && 
                            <button 
                                className={`${styles.submitBtn} ${gStyles.clickable} ${!review.valid ? styles.submitDisabled : ''}`} 
                                title={!review.valid ? "Fix errors to submit" : "Submit Changes"}
                                onClick={() => {
                                    if (review.valid) {
                                        handleSubmit();
                                    }
                                }}
                                disabled={!review.valid}>
                                <span className={styles.btnText}>
                                    {!review.valid ? 'Fix errors to submit' : 'Save changes to history'}
                                </span>
                                <FaCircleCheck />
                            </button>
                        }

                        {review && hasChanges &&
                        <PipelineReview review={review} isReviewOpen={isReviewOpen}
                            setIsReviewOpen={setIsReviewOpen} handleSubmit={handleSubmit}/>
                        }

                        {hasChanges && 
                            <button className={`${styles.validBtn} ${gStyles.clickable}`}
                                onClick={reviewJobs} disabled={isReviewing}>
                                <span className={styles.btnText}>
                                    {isReviewing ? "Checking..." : "Check for Errors"}
                                </span>
                                <MdFactCheck/>
                            </button>
                        }

                        <button className={`${styles.discardBtn} ${gStyles.clickable}`} title="Discard Changes"
                            onClick={() => {
                                hasChanges ? (
                                    setAskDiscard("Discard all changes?"),
                                    setWarningDiscard("This Action can not be undone!")
                                ) : setIsEdit(false)
                            }}><span className={styles.btnText}>{hasChanges?"Discard Changes":"Close Editor"}</span><IoClose/></button>
                    </div>

                    {jobs.map((job, jobIndex) => {
                        let lines = job.content.split("\n");
                        lineNumber += lines.length;
                        return (
                            <SortableJob
                                key={job.id}
                                job={job}
                                jobIndex={jobIndex}
                                moveJob={moveJob}
                                updateJobContent={updateJobContent}
                                deleteJob={deleteJob}
                                handleKeyDown={handleTabKeyDown}
                            />
                        );
                    })}

                    <div className={`${styles.themeBtn} ${isDark ? styles.dark : ""}`}
                        onClick={() => setIsDark(!isDark)} title="Change Theme">
                        <MdBrightness6 className={styles.sunIcon} />
                        <MdBrightness2 className={styles.moonIcon} />
                    </div>
                    <ChatbotBubble
                        isChatOpen={isChatOpen}
                        setIsChatOpen={setIsChatOpen}
                    />
                    <div ref={jobsEndRef} />
                </div>

                {askDiscard && 
                <Popup
                    btnText1="Discard"
                    btn1Action={()=> setDiscardChanges(true)}
                    btnText2="Cancel"
                    questionMessage={askDiscard}
                    setQuestionMessage={setAskDiscard}
                    warningMessage={warningDiscard}
                    setWarningMessage={setWarningDiscard}
                />}
                {askSubmit && 
                <Popup
                    btnText1="Submit"
                    btn1Action={()=> {submitJobs(); setIsEdit(false);}}
                    btnText2="Cancel"
                    questionMessage={askSubmit}
                    setQuestionMessage={setAskSubmit}
                    warningMessage={warningSubmit}
                    setWarningMessage={setWarningSubmit}
                />}
                {(confirmSubmit || errorSubmit) && 
                <Popup
                    btnText1="Got it"
                    confirmMessage={confirmSubmit}
                    setConfirmMessage={setConfirmSubmit}
                    errorMessage={errorSubmit}
                    setErrorMessage={setErrorSubmit}
                    popupRef={popupRef}
                />}
            </SortableContext>
        </DndContext>
    );
}

export default PipelineEditor;
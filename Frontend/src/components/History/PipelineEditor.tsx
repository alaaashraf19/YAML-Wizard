import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'

import ChatbotBubble from "./ChatbotBubble";
import SortableJob from './SortableJob';
import type { Job, Pipeline, Project } from "../../types";
import { useEffect, useRef, useState, useCallback } from "react";

import { FaCircleCheck } from "react-icons/fa6";
import { IoClose } from "react-icons/io5";
import { MdBrightness6 } from "react-icons/md";
import { MdBrightness2 } from "react-icons/md";

import { DndContext, type DragEndEvent } from "@dnd-kit/core";
import { arrayMove, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

type EditorProps = {
    project: Project,
    pipeline: Pipeline,
    setIsEdit: React.Dispatch<React.SetStateAction<boolean>>,
    isDark: boolean,
    setIsDark: React.Dispatch<React.SetStateAction<boolean>>,
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

function PipelineEditor({ project, pipeline, setIsEdit, isDark, setIsDark }: EditorProps) {
    const jobsEndRef = useRef<HTMLDivElement | null>(null);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const jobIdCounter = useRef(0);
    
    const [jobs, setJobs] = useState<Job[]>([
        {
            id: "build",
            content: "build:\n  stage: build\n  script:\n    - npm install\n    - npm run build"
        },
        {
            id: "test",
            content: "test:\n  stage: test\n  script:\n    - npm test"
        },
        {
            id: "deploy",
            content: "deploy:\n  stage: deploy\n  script:\n    - npm run deploy"
        }
    ]);
    
    const [_, setHistory] = useState<HistoryState>({
        snapshots: [{ jobs: structuredClone(jobs), type: 'structural' }],
        index: 0
    });
    
    // Use ref instead of state to avoid re-renders
    const isRestoringFromHistory = useRef(false);
    const isUndoRedoInProgress = useRef(false);

    const generateJobId = useCallback(() => {
        jobIdCounter.current += 1;
        return `job_${Date.now()}_${jobIdCounter.current}`;
    }, []);

    // Save functions with proper typing
    const saveHistory = useCallback((jobs: Job[], type: HistoryEntry['type'], extraInfo?: any) => {
        const snapshot = structuredClone(jobs);
        setHistory(prev => {
            const snapshots = prev.snapshots.slice(0, prev.index + 1);
            const entry: HistoryEntry = { jobs: snapshot, type };
            
            if (type === 'tab' && extraInfo) {
                entry.tabInfo = extraInfo;
            } else if (type === 'text' && extraInfo) {
                entry.textInfo = extraInfo;
            }
            
            snapshots.push(entry);
            return {
                snapshots,
                index: snapshots.length - 1,
            };
        });
    }, []);

    const saveStructuralChange = useCallback((newJobs: Job[]) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'structural');
    }, [saveHistory]);

    const saveTabChange = useCallback((newJobs: Job[], jobIndex: number, start: number, end: number, textBefore: string, textAfter: string) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'tab', { jobIndex, start, end, textBefore, textAfter });
    }, [saveHistory]);

    const saveTextChange = useCallback((newJobs: Job[], jobIndex: number, content: string) => {
        setJobs(newJobs);
        saveHistory(newJobs, 'text', { jobIndex, content });
    }, [saveHistory]);

    // Text change handler with flag check
    const updateJobContent = useCallback((jobIndex: number, content: string) => {
        // Skip saving if we're restoring from history
        if (isRestoringFromHistory.current) return;
        
        const newJobs = [...jobs];
        newJobs[jobIndex] = { ...newJobs[jobIndex], content };
        saveTextChange(newJobs, jobIndex, content);
    }, [jobs, saveTextChange]);

    // Undo function
    const undo = useCallback(() => {
        if (isUndoRedoInProgress.current) return;
        
        setHistory(prev => {
            if (prev.index <= 0) return prev;
            
            const currentEntry = prev.snapshots[prev.index];
            const previousEntry = prev.snapshots[prev.index - 1];
            const nextIndex = prev.index - 1;
            
            // Set flags
            isUndoRedoInProgress.current = true;
            isRestoringFromHistory.current = true;
            
            // Handle tab undo
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
            
            // Restore job state
            setJobs(structuredClone(previousEntry.jobs));
            
            // Clear flags after state updates
            setTimeout(() => {
                isRestoringFromHistory.current = false;
                isUndoRedoInProgress.current = false;
            }, 50);
            
            return {
                ...prev,
                index: nextIndex,
            };
        });
    }, []);

    // Redo function
    const redo = useCallback(() => {
        if (isUndoRedoInProgress.current) return;
        
        setHistory(prev => {
            if (prev.index >= prev.snapshots.length - 1) return prev;
            
            const nextEntry = prev.snapshots[prev.index + 1];
            const nextIndex = prev.index + 1;
            
            // Set flags
            isUndoRedoInProgress.current = true;
            isRestoringFromHistory.current = true;
            
            // Handle tab redo
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
            
            // Restore job state
            setJobs(structuredClone(nextEntry.jobs));
            
            // Clear flags after state updates
            setTimeout(() => {
                isRestoringFromHistory.current = false;
                isUndoRedoInProgress.current = false;
            }, 50);
            
            return {
                ...prev,
                index: nextIndex,
            };
        });
    }, []);

    // Tab key handler
    const handleTabKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>, jobIndex: number) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const textarea = e.currentTarget;
            const { selectionStart, selectionEnd, value } = textarea;
            const tab = "  ";
            
            const textBefore = value;
            const newValue = value.slice(0, selectionStart) + tab + value.slice(selectionEnd);
            const textAfter = newValue;
            
            const newJobs = [...jobs];
            newJobs[jobIndex] = { ...newJobs[jobIndex], content: newValue };
            
            saveTabChange(newJobs, jobIndex, selectionStart, selectionEnd, textBefore, textAfter);
            
            requestAnimationFrame(() => {
                textarea.setSelectionRange(selectionStart + tab.length, selectionStart + tab.length);
            });
        }
    }, [jobs, saveTabChange]);

    // Keyboard shortcuts handler
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Don't intercept if we're in the middle of an operation
            if (isUndoRedoInProgress.current) return;
            
            // Check if Ctrl/Cmd is pressed
            if (!(e.ctrlKey || e.metaKey)) return;
            // For undo (Ctrl+Z)
            if (e.key.toLowerCase() === "z") {
                // Don't prevent default if we're in an input and there's browser history
                // But we'll handle all undo operations ourselves
                e.preventDefault();
                undo();
                return;
            }
            
            // For redo (Ctrl+Y or Ctrl+Shift+Z)
            if (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey)) {
                e.preventDefault();
                redo();
                return;
            }
        };
        
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [undo, redo]);

    // Job operation functions
    const moveJob = useCallback((index: number, direction: -1 | 1) => {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= jobs.length) return;

        const copy = [...jobs];
        [copy[index], copy[newIndex]] = [copy[newIndex], copy[index]];

        saveStructuralChange(copy);
    }, [jobs, saveStructuralChange]);

    const addJob = useCallback(() => {
        const newJobs = [...jobs, {
            id: generateJobId(),
            content: "new_job:\n  stage:\n  script:"
        }];
        saveStructuralChange(newJobs);
    }, [jobs, generateJobId, saveStructuralChange]);

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
                        <button className={`${styles.discardBtn} ${gStyles.clickable}`} title="Discard Changes"
                            onClick={() => setIsEdit(false)}><IoClose /></button>
                        <button className={`${styles.submitBtn} ${gStyles.clickable}`} title="Submit Changes"><FaCircleCheck /></button>
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
                        onClick={() => setIsDark(prev => !prev)} title="Change Theme">
                        <MdBrightness6 className={styles.sunIcon} />
                        <MdBrightness2 className={styles.moonIcon} />
                    </div>
                    <ChatbotBubble
                        project={project}
                        pipeline={pipeline}
                        isChatOpen={isChatOpen}
                        setIsChatOpen={setIsChatOpen}
                    />
                    <div ref={jobsEndRef} />
                </div>
            </SortableContext>
        </DndContext>
    );
}

export default PipelineEditor;
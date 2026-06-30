import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'

import ChatbotBubble from "./ChatbotBubble";
import SortableJob from './SortableJob';
import type { Job } from "../../types";
import { useEffect, useRef, useState, useCallback } from "react";

import { FaCircleCheck } from "react-icons/fa6";
import { IoClose } from "react-icons/io5";
import { MdBrightness6 } from "react-icons/md";
import { MdBrightness2 } from "react-icons/md";

import { DndContext, type DragEndEvent } from "@dnd-kit/core";
import { arrayMove, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

import { useHistoryStore } from "../../pages/History";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import Popup from "../Popup/Popup";


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
    jobs: Job[],
    setJobs: (jobs: Job[]) => void,
    
    history: HistoryState,
    setHistory: (history: HistoryState) => void,

    originalJobs: Job[],
    setOriginalJobs: (jobs: Job[]) => void,

    hasChanges: boolean;
    setHasChanges: (hasChanges: boolean) => void,

    initializeEditor: (jobs: Job[]) => void;

    resetEditor: () => void;

    saveChanges: (onSave: (jobs: Job[]) => void) => void;
}

const useEditorStore = create<EditorStore>()(
    persist(
        (set, get) => ({
            jobs: [],
            setJobs: (jobs) => set({ jobs }),

            originalJobs: [],
            setOriginalJobs: (jobs) => set({ originalJobs: jobs }),

            hasChanges: false,
            setHasChanges: (hasChanges) => set({ hasChanges }),

            history: { snapshots: [], index: 0 },
            setHistory: (history) => set({ history }),

            initializeEditor: (jobs: Job[]) => {
                const currentHistory = get().history;
                
                if (currentHistory.snapshots.length > 0) {
                    const persistedJobs = currentHistory.snapshots[currentHistory.index]?.jobs;                    
                    if (persistedJobs && JSON.stringify(persistedJobs) === JSON.stringify(jobs)) {
                        set({
                            jobs: structuredClone(persistedJobs),
                            originalJobs: structuredClone(jobs),
                        });
                        return;
                    }
                }
                
                const initialSnapshot: HistoryEntry = {
                    jobs: structuredClone(jobs),
                    type: 'structural'
                };
                
                set({
                    jobs: structuredClone(jobs),
                    originalJobs: structuredClone(jobs),
                    history: {
                        snapshots: [initialSnapshot],
                        index: 0,
                    },
                    hasChanges: false,
                });
            },

            resetEditor: () => {
                const originalJobs = get().originalJobs;
                if (originalJobs.length === 0) return;
                
                const initialSnapshot: HistoryEntry = {
                    jobs: structuredClone(originalJobs),
                    type: 'structural'
                };
                
                set({
                    jobs: structuredClone(originalJobs),
                    history: {
                        snapshots: [initialSnapshot],
                        index: 0,
                    },
                    hasChanges: false,
                });
                sessionStorage.removeItem('editor_store');
            },

            saveChanges: (onSave: (jobs: Job[]) => void) => {
                const currentJobs = get().jobs;
                onSave(currentJobs);
                set({ 
                    hasChanges: false,
                    originalJobs: structuredClone(currentJobs)
                });
            },
        }),
        {
            name: "editor_store",
            storage: createJSONStorage(() => sessionStorage),
            // only persist history
            partialize: (state) => ({history: state.history,}),
        }
    )
);

function PipelineEditor({ initJobs, isDiscardChanges, setDiscardChanges, setInitJobs }: EditorProps) {
    const MAX_SNAPSHOTS = 50;
    const {isDark, setIsDark, setIsEdit} = useHistoryStore();

    const {jobs, setJobs, history, setHistory, setHasChanges,
        resetEditor, initializeEditor} = useEditorStore();

    const [isChatOpen, setIsChatOpen] = useState(false);
    const [askDiscard, setAskDiscard] = useState<string | null>(null);
    const [warningDiscard, setWarningDiscard] = useState<string | null>(null);
    const [confirmSubmit, setConfirmSubmit] = useState<string | null>(null);
    const [errorSubmit, setErrorSubmit] = useState<string | null>(null);

    const isInitialized = useRef(false);
    const prevInitJobsRef = useRef<Job[]>([]);
    const jobsEndRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement>(null);

    // Handle discard
    const handleNewEditor = () => {
        resetEditor();
        setIsEdit(false);
    };
    useEffect(()=>{
        if(isDiscardChanges){
            handleNewEditor();
            setDiscardChanges(false);
        }
    }, [isDiscardChanges]);

    // initialize editor only if there is no history
    useEffect(() => {
        if (initJobs.length === 0) return;
        if (isInitialized.current) return;
        
        const hasPersistedHistory = history.snapshots.length > 0;
        
        if (hasPersistedHistory) {
            const persistedJobs = history.snapshots[history.index]?.jobs;
            if (persistedJobs) {
                setJobs(structuredClone(persistedJobs));
                isInitialized.current = true;
                prevInitJobsRef.current = structuredClone(initJobs);
                return;
            }
        }
        
        initializeEditor(initJobs);
        isInitialized.current = true;
        prevInitJobsRef.current = structuredClone(initJobs);
    }, [initJobs, initializeEditor, history.snapshots, history.index, setJobs]);
    
    // ref instead of state to avoid re-renders
    const isRestoringFromHistory = useRef(false);
    const isUndoRedoInProgress = useRef(false);
        
    const jobIdCounter = useRef(0);
    const generateJobId = useCallback(() => {
        jobIdCounter.current += 1;
        return `job_${Date.now()}_${jobIdCounter.current}`;
    }, []);

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
                snapshots = snapshots.slice(-30); // Keep only last 30
            }
            setHistory({ snapshots, index: snapshots.length - 1 });
        }
        
        if (type !== 'text') {
            setHasChanges(true);
        }
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
        // Skip saving if we're restoring from history
        if (isRestoringFromHistory.current) return;
        
        const newJobs = [...jobs];
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
        
        // handle tab undo
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
        
        // handle tab redo
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
                            onClick={() => {
                                setAskDiscard("Discard all changes?");
                                setWarningDiscard("This Action can not be undone!");
                            }}><IoClose /></button>
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
                    btn1Action={handleNewEditor}
                    btnText2="Cancel"
                    questionMessage={askDiscard}
                    setQuestionMessage={setAskDiscard}
                    warningMessage={warningDiscard}
                    setWarningMessage={setWarningDiscard}
                    popupRef={popupRef}
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
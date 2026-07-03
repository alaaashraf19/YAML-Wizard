import styles from './History.module.css'

import PipelineEditor from "../components/History/PipelineEditor";
import PipelineViewer from "../components/History/PipelineViewer";
import HProjects from "../components/History/HProjects";
import Popup from '../components/Popup/Popup';

import type { Job, Pipeline, Project } from "../types";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { IoIosArrowDropdownCircle } from "react-icons/io";
import HistoryBar from '../components/History/HistoryBar';

import {create} from "zustand";
import {persist,createJSONStorage} from "zustand/middleware";


type HistoryStore = {
    isEdit: boolean;
    setIsEdit: (isEdit: boolean)=>void;
    
    isExpanded: boolean;
    setIsExpanded: (isExpanded: boolean)=>void;

    isDark: boolean;
    setIsDark: (isDark: boolean)=>void;

    loadingSync: boolean;
    setLoadingSync: (loadingSync: boolean)=>void;

    project: Project | null,
    setProject: (project: Project | null)=>void,

    pipeline: Pipeline | null,
    setPipeline: (pipeline: Pipeline | null)=>void,

    version: Pipeline | null,
    setVersion: (pipeline: Pipeline | null)=>void,
}

export const useHistoryStore = create<HistoryStore>()(
    persist((set)=> ({
        isEdit: false,
        setIsEdit: isEdit =>set({isEdit}),

        isExpanded: false,
        setIsExpanded: isExpanded => set({isExpanded}),

        isDark: false,
        setIsDark: isDark => set({isDark}),

        loadingSync: false,
        setLoadingSync: loadingSync => set({loadingSync}),
        
        project: null,
        setProject: project=>set({project}),
        
        pipeline: null,
        setPipeline: pipeline=>set({pipeline}),
        
        version: null,
        setVersion: version=>set({version}),
    }),{
        name: "history_store",
        storage: createJSONStorage(() => sessionStorage)
    })
);


function History(){
    const {isEdit, isExpanded, setIsExpanded, setLoadingSync, project, pipeline, version, setPipeline} = useHistoryStore();

    const [jobs, setJobs] = useState<Job[]>([]);
    const [pipelines, setPipelines] = useState<Pipeline[]>([]);
    const [isDiscardChanges, setDiscardChanges] = useState<boolean> (false);
    const [confirmSync, setConfirmSync] = useState<string | null>(null);

    const topContentRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;
    

    const currentProjectIdRef = useRef<number | null>(null);
    
    // Load cached pipelines if syncing
    useEffect(()=> {
        currentProjectIdRef.current = project?.id || null;
        if(project && sessionStorage.getItem(`${project.id}_syncing`)){
            setLoadingSync(true);
            setPipelines(JSON.parse(sessionStorage.getItem(`${project.id}_cached_ pipelines`) || "[]"));
        } else if(project){
            setLoadingSync(false);
        }
    }, [project?.id]);

    // clear pipeline if project or pipelines are not available
    useEffect(()=> {
        if(!project || !pipelines) setPipeline(null);
        console.log("Project or pipelines not available, clearing pipeline");
    }, [pipelines]);

    // //get project pipelines, or sync if not synced
    useEffect(() => {
        const checkSynced = async (currentProjectId: number) =>{
            if (!currentProjectId) return false;

            const syncKey = `${currentProjectId}_pipelines_synced`;
            const isSynced = sessionStorage.getItem(syncKey);

            if(!isSynced){
                await syncPipelines();
                return true;
            }
            return false;
        }

        const fetchPipelines = async (currentProjectId: number) => {
            
            try {
                const res = await fetch(`${api_url}/pipelines/project/${currentProjectId}`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipelines");
                    return;
                }
                if(currentProjectId === project?.id) setPipelines(data);
                
            } catch (e) {
                console.error("Failed to fetch pipelines:", e);
            }
        };

        const init = async () => {
            const currentProjectId = project?.id;
            if(!currentProjectId)return;

            const fetchedBySynced = await checkSynced(currentProjectId);
            if(!fetchedBySynced) await fetchPipelines(currentProjectId);
        };

        if(project)init();
    }, [project]);
    // sync and don't update pipelines if not changed  
    const syncPipelines: ()=>Promise<boolean> = async ()=> {
        if (!project) return false;
        
        const syncingProjectId = currentProjectIdRef.current;
        const syncingKey = `${syncingProjectId}_syncing`;
        sessionStorage.setItem(syncingKey, true.toString());

        console.log("...Syncing project :", syncingProjectId);
        setLoadingSync(true);
        try {
            const res = await fetch(`${api_url}/pipelines/${project?.id}/sync`, {
                credentials: "include",
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to sync pipelines");
                setLoadingSync(false);
                return false;
            }

            const currentProjectId = currentProjectIdRef.current;

            const syncKey = `${syncingProjectId}_pipelines_synced`;
            const cacheKey = `${syncingProjectId}_cached_pipelines`;
            const lastSyncedKey  = `${syncingProjectId}_last_synced`;

            const isSynced = sessionStorage.getItem(syncKey);
            const storedData = sessionStorage.getItem(cacheKey);

            if(isSynced === 'true'){
                if (JSON.stringify(data) !== storedData) {
                    syncingProjectId === currentProjectId && setPipelines(data);
                    sessionStorage.setItem(cacheKey, JSON.stringify(data));
                    sessionStorage.setItem(lastSyncedKey, new Date().toISOString());
                }
                else{
                    setLoadingSync(false);
                    sessionStorage.removeItem(syncingKey);
                    setConfirmSync(`Pipelines of project ${project?.project_name} are already up to date.`)
                    return false;
                }
            }else{
                syncingProjectId === currentProjectId && setPipelines(data);
                sessionStorage.setItem(cacheKey, JSON.stringify(data));
                sessionStorage.setItem(syncKey, 'true');
                sessionStorage.setItem(lastSyncedKey, new Date().toISOString());
            }
            
            setConfirmSync(`Pipelines of project ${project?.project_name} have been synced successfully.`)
            console.log("Sync Completed for project:", syncingProjectId);
            
            sessionStorage.removeItem(syncingKey);
            setLoadingSync(false);
            return true;

        } catch (e) {
            console.error("Failed to sync pipelines:", e);
            setLoadingSync(false);
            sessionStorage.removeItem(syncingKey);
            return false;
        }
    };

    //get jobs
    useEffect(()=> {
        if(!pipeline || !project) return;
        const getJobs = async () => {
            try {
                const res = await fetch(`${api_url}/projects/${project?.id}/pipelines/${pipeline?.id}/jobs`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });
    
                const data = await res.json();
    
                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipeline script");
                    return;
                }
                setJobs(data.jobs);
            }catch(e: any){
                console.error(`Failed to get jobs of pipeline with id: ${pipeline?.id}`)
            }
        }
        getJobs();
    },[pipeline?.id]);


    // make top bar scroll to top on collapsing
    useEffect(()=>{
        if(!isExpanded){
            topContentRef.current?.scrollTo({ top: 0, behavior:"smooth"});
        }
    },[isExpanded]);

    const getLastSyncedText = () => {
        const lastSyncedKey =`${project?.id}_last_synced`;
        const lastSynced = sessionStorage.getItem(lastSyncedKey);
        return (lastSynced ? "Last Synced ("+new Date(lastSynced).toLocaleString()+")" : "Never Synced")
    }

    let currentActive: Pipeline | null  = pipeline ? pipeline : version ? version : null;

    return(
        <div className={styles.window}>
            <HProjects isEdit={isEdit} setDiscardChanges={setDiscardChanges }/>

            <div className={styles.historyContainer}>
                {project && <div className={`${styles.topBar} ${isExpanded && styles.expanded}`}>
                    <div className={styles.topBarContent} ref={topContentRef}>
                        <Link title="Go to link" target="_blank"
                            className={`${styles.barTab} ${styles.barLink}`} to={project.repo_url}>
                            {project.repo_url}</Link>
                        <span className={styles.barTab}>{getLastSyncedText()}</span>

                        {currentActive && <>
                            <span className={styles.barTab}>{currentActive.name}</span>
                            <span className={styles.barTab}>{currentActive.is_active?"Published":"Not-Published"}</span>
                            <Link className={`${styles.barTab} ${styles.barLink}`} title="Go to link" target="_blank"
                                to={`${project.repo_url}/tree/${project.branch}/${currentActive.path}`}>
                                {currentActive.path ?? "Path Unknown"}</Link>
                            <span className={styles.barTab}>{project.branch ?? "Branch Unknown"}</span>
                            {/* <span className={styles.barTab}>Commit Hash ({currentActive.commit_hash})</span> */}
                            <span className={styles.barTab}>{currentActive.commit_author ?? "Author Unknown"}</span>
                            <span className={styles.barTab}>Created ({
                            new Date(currentActive.created_at).toLocaleString() ?? "Unknown"})</span>
                            <span className={styles.barTab}>Last Updated ({
                                new Date(currentActive.updated_at).toLocaleString() ?? "Unknown"})</span>
                            {currentActive.is_active && 
                            <span className={styles.barTab}>Published ({
                                new Date(currentActive.commited_at).toLocaleString() ?? "Unknown"})</span>}
                        </>}
                    </div>
                    <button className={styles.expandBtn} onClick={()=>setIsExpanded(!isExpanded)}>
                        <IoIosArrowDropdownCircle/> </button>
                </div>}
                <div className={styles.historyWindow}>
                    <HistoryBar pipelines={pipelines} setPipelines={setPipelines} setJobs={setJobs}
                        syncPipelines={syncPipelines} setDiscardChanges ={setDiscardChanges } />
                    {(project && currentActive)?
                        (isEdit ? <PipelineEditor initJobs={jobs} setInitJobs={setJobs} 
                            isDiscardChanges={isDiscardChanges} setDiscardChanges={setDiscardChanges}/>
                            : <PipelineViewer jobs={jobs}/>
                    ) : <div className={styles.noPipeline}>
                        <p className={styles.noPipelineHeader}>YAML Wizard Version History</p>
                        <p className={styles.noPipelineSubHeader}>Add your project and pick a pipeline to get started.</p>
                    </div>}
                        
                </div>
            </div>
            {confirmSync && <Popup
                btnText1="Got it"
                confirmMessage={confirmSync}
                setConfirmMessage={setConfirmSync}
                popupRef={popupRef}
            />}
        </div>
    );
}

export default History;
import styles from './History.module.css'

import PipelineEditor from "../components/History/PipelineEditor";
import PipelineViewer from "../components/History/PipelineViewer";
import HProjects from "../components/History/HProjects";

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
    }),{
        name: "history_store",
        storage: createJSONStorage(() => sessionStorage)
    })
);


function History(){
    const {isEdit, isExpanded, setIsExpanded, setLoadingSync, project, pipeline} = useHistoryStore();

    const [jobs, setJobs] = useState<Job[]>([]);
    const [pipelines, setPipelines] = useState<Pipeline[]>([]);
    const [lastSynced, setLastSynced] = useState<string | null>(null);
    const [isDiscardChanges, setDiscardChanges] = useState<boolean> (false);

    const topContentRef = useRef<HTMLDivElement | null>(null);
    const api_url = import.meta.env.VITE_API_URL;
    
    // //get project pipelines, or sync if not synced
    useEffect(() => {
        const checkSynced = async () =>{
            const isSynced = sessionStorage.getItem('pipelines_synced');
            if(!isSynced){
                await syncPipelines();
                return true;
            }
            return false;
        }

        const fetchPipelines = async () => {
            try {
                const res = await fetch(`${api_url}/pipelines/project/${project?.id}`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipelines");
                    return;
                }
                setPipelines(data);
                
            } catch (e) {
                console.error("Failed to fetch pipelines:", e);
            }
        };

        const init = async () => {
            const fetchedBySynced = await checkSynced();
            if(!fetchedBySynced) await fetchPipelines();
        };

        console.log("Project id now is:", project?.id);
        if(project)init();
    }, [project]);
    // sync and don't update pipelines if not changed  
    const syncPipelines: ()=>Promise<boolean> = async ()=> {
        if (!project) return false;

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

            const isSynced = sessionStorage.getItem('pipelines_synced');
            const storedData = sessionStorage.getItem('cached_pipelines');

            if(isSynced === 'true'){
                if (JSON.stringify(data) !== storedData) {
                    setPipelines(data);
                    sessionStorage.setItem('cached_pipelines', JSON.stringify(data));
                    setLastSynced(new Date().toISOString());
                }
                else{
                    setLoadingSync(false);
                    return false;
                }
            }else{
                setPipelines(data);
                sessionStorage.setItem('cached_pipelines', JSON.stringify(data));
                sessionStorage.setItem('pipelines_synced', 'true');
                setLastSynced(new Date().toISOString());
            }
            console.log("Sync Completed");
            setLoadingSync(false);
            return true;

        } catch (e) {
            console.error("Failed to sync pipelines:", e);
            setLoadingSync(false);
            return false;
        }
    };

    //get jobs
    useEffect(()=> {
        if(!pipeline || !project) return;

        const getJobs = async () => {
            try {
                const res = await fetch(`${api_url}/projects/${project.id}/pipelines/${pipeline.id}/jobs`, {
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
                console.error(`Failed to get jobs of pipeline with id: ${pipeline.id}`)
            }
        }

        if(pipeline)getJobs();
    },[pipeline]);


    // make top bar scroll to top on collapsing
    useEffect(()=>{
        if(!isExpanded){
            topContentRef.current?.scrollTo({ top: 0, behavior:"smooth"});
        }
    },[isExpanded]);

    return(
        <div className={styles.window}>
            <HProjects isEdit={isEdit} setDiscardChanges={setDiscardChanges }/>

            <div className={styles.historyContainer}>
                {project && <div className={`${styles.topBar} ${isExpanded && styles.expanded}`}>
                    <div className={styles.topBarContent} ref={topContentRef}>
                        <Link title="Go to link" target="_blank"
                            className={`${styles.barTab} ${styles.barLink}`} to={project.repo_url}>
                            {project.repo_url}</Link>
                        <span className={styles.barTab}>
                            {lastSynced ? "Last Synced ("+new Date(lastSynced).toLocaleString()+")" : "Never Synced"}</span>

                        {pipeline && <>
                            <span className={styles.barTab}>{pipeline.name}</span>
                            <Link className={`${styles.barTab} ${styles.barLink}`} title="Go to link" target="_blank"
                                to={`${project.repo_url}/tree/${project.branch}/${pipeline.path}`}>{pipeline.path}</Link>
                            <span className={styles.barTab}>{project.branch}</span>
                            <span className={styles.barTab}>Commit Hash ({pipeline.commit_hash})</span>
                            <span className={styles.barTab}>{pipeline.commit_author}</span>
                            <span className={styles.barTab}>{pipeline.is_active?"Published":"Not-Published"}</span>
                            <span className={styles.barTab}>Created ({new Date(pipeline.created_at).toLocaleString()})</span>
                            <span className={styles.barTab}>Last Updated ({new Date(pipeline.updated_at).toLocaleString()})</span>
                            {pipeline.is_active && 
                            <span className={styles.barTab}>Published ({new Date(pipeline.activated_at).toLocaleString()})</span>}
                        </>}
                    </div>
                    <button className={styles.expandBtn} onClick={()=>setIsExpanded(!isExpanded)}>
                        <IoIosArrowDropdownCircle/> </button>
                </div>}
                <div className={styles.historyWindow}>
                    <HistoryBar pipelines={pipelines} setPipelines={setPipelines} 
                        syncPipelines={syncPipelines} setDiscardChanges ={setDiscardChanges } />
                    {(project && pipeline)?
                        (isEdit ? <PipelineEditor initJobs={jobs} setInitJobs={setJobs} 
                            isDiscardChanges={isDiscardChanges} setDiscardChanges={setDiscardChanges}/>
                            : <PipelineViewer jobs={jobs}/>
                    ) : <div className={styles.noPipeline}>
                        <p className={styles.noPipelineHeader}>YAML Wizard Version History</p>
                        <p className={styles.noPipelineSubHeader}>Add your project and pick a pipeline to get started.</p>
                    </div>}
                        
                </div>
            </div>
        </div>
    );
}

export default History;
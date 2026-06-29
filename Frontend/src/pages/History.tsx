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

    project: Project | null,
    setProject: (project: Project | null)=>void,

    // projects: Project[],
    // setProjects: (projects: Project[])=>void,

    pipeline: Pipeline | null,
    setPipeline: (pipeline: Pipeline | null)=>void,

    // pipelines: Pipeline[],
    // setPipelines: (pipelines: Pipeline[])=>void,

    // jobs: Job[],
    // setJobs: (jobs: Job[]) => void,
}

export const useHistoryStore = create<HistoryStore>()(
    persist((set)=> ({
        isEdit: false,
        setIsEdit: isEdit =>set({isEdit}),

        isExpanded: false,
        setIsExpanded: isExpanded => set({isExpanded}),

        isDark: false,
        setIsDark: isDark => set({isDark}),
        
        project: null,
        setProject: project=>set({project}),
        
        // projects: [],
        // setProjects: projects=>set({projects}),
        
        pipeline: null,
        setPipeline: pipeline=>set({pipeline}),
        
        // pipelines: [
        //     {
        //     "id": 0,
        //     "name": "string",
        //     "author": "author0",
        //     "commit_hash": "string",
        //     "branch": "branch0",
        //     "path": "path0",
        //     "content": "string",
        //     "is_active": true,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": false
        //     },
        //     {
        //     "id": 1,
        //     "name": "stringstringstringstring",
        //     "author": "author1",
        //     "commit_hash": "string",
        //     "branch": "branch1",
        //     "path": "path1",
        //     "content": "string",
        //     "is_active": true,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        //     {
        //     "id": 2,
        //     "name": "string",
        //     "author": "author2",
        //     "commit_hash": "string",
        //     "branch": "branch2",
        //     "path": "path2",
        //     "content": "string",
        //     "is_active": false,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        //     {
        //     "id": 3,
        //     "name": "string",
        //     "author": "author3",
        //     "commit_hash": "string",
        //     "branch": "branch3",
        //     "path": "path3",
        //     "content": "string",
        //     "is_active": false,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        //     {
        //     "id": 4,
        //     "name": "string",
        //     "author": "author4",
        //     "commit_hash": "string",
        //     "branch": "branch4",
        //     "path": "path4",
        //     "content": "string",
        //     "is_active": false,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        //     {
        //     "id": 5,
        //     "name": "string",
        //     "author": "author5",
        //     "commit_hash": "string",
        //     "branch": "branch5",
        //     "path": "path5",
        //     "content": "string",
        //     "is_active": false,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        //     {
        //     "id": 6,
        //     "name": "string",
        //     "author": "author6",
        //     "commit_hash": "string",
        //     "branch": "branch6",
        //     "path": "path6",
        //     "content": "string",
        //     "is_active": false,
        //     "created_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        //     "is_generated_by_wizard": true
        //     },
        // ],
        // setPipelines: pipelines=>set({pipelines}),
        
        // jobs: [
        //     {
        //         id: "build",
        //         content: "build:\n  stage: build\n  script:\n    - npm install\n    - npm run build"
        //     },
        //     {
        //         id: "test",
        //         content: "test:\n  stage: test\n  script:\n    - npm test"
        //     },
        //     {
        //         id: "deploy",
        //         content: "deploy:\n  stage: deploy\n  script:\n    - npm run deploy"
        //     }
        // ],
        // setJobs: jobs=>set({jobs}),
    }),{
        name: "history_store",
        storage: createJSONStorage(() => sessionStorage)
    })
);

//on project change set pipelines
function History(){
    // const isEdit = useHistoryStore(s=>s.isEdit);
    // const isExpanded = useHistoryStore(s=>s.isExpanded);
    // const setIsExpanded = useHistoryStore(s=>s.setIsExpanded);
    const {isEdit, isExpanded, setIsExpanded, project, pipeline} = useHistoryStore();

    // const project = useHistoryStore(s=>s.project);
    // const pipeline = useHistoryStore(s=>s.pipeline);
    // const setProjects = useHistoryStore(s=>s.setProjects);
    // const setPipelines = useHistoryStore(s=>s.setPipelines);
    // const setJobs = useHistoryStore(s=>s.setJobs);
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
    
    const [pipelines, setPipelines] = useState<Pipeline[]>([
        {
        "id": 0,
        "name": "string",
        "author": "author0",
        "commit_hash": "string",
        "branch": "branch0",
        "path": "path0",
        "content": "string",
        "is_active": true,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": false
        },
        {
        "id": 1,
        "name": "stringstringstringstring",
        "author": "author1",
        "commit_hash": "string",
        "branch": "branch1",
        "path": "path1",
        "content": "string",
        "is_active": true,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
        {
        "id": 2,
        "name": "string",
        "author": "author2",
        "commit_hash": "string",
        "branch": "branch2",
        "path": "path2",
        "content": "string",
        "is_active": false,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
        {
        "id": 3,
        "name": "string",
        "author": "author3",
        "commit_hash": "string",
        "branch": "branch3",
        "path": "path3",
        "content": "string",
        "is_active": false,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
        {
        "id": 4,
        "name": "string",
        "author": "author4",
        "commit_hash": "string",
        "branch": "branch4",
        "path": "path4",
        "content": "string",
        "is_active": false,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
        {
        "id": 5,
        "name": "string",
        "author": "author5",
        "commit_hash": "string",
        "branch": "branch5",
        "path": "path5",
        "content": "string",
        "is_active": false,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
        {
        "id": 6,
        "name": "string",
        "author": "author6",
        "commit_hash": "string",
        "branch": "branch6",
        "path": "path6",
        "content": "string",
        "is_active": false,
        "created_at": new Date("2026-06-25T03:47:51.317Z"),
        "updated_at": new Date("2026-06-25T03:47:51.317Z"),
        "activated_at": new Date("2026-06-25T03:47:51.317Z"),
        "is_generated_by_wizard": true
        },
    ]);

    //setPipeline null before sync
    const [lastSynced, setLastSynced] = useState<Date | null>(null);

    const topContentRef = useRef<HTMLDivElement | null>(null);
    const api_url = import.meta.env.VITE_API_URL;
    
    // //get project pipelines
    // useEffect(() => {
    //     const fetchPipelines = async () => {
    //         try {
    //             const res = await fetch(`${api_url}/projects/${project?.id}/pipelines`, {
    //                 credentials: "include",
    //                 method: "GET",
    //                 headers: {"Content-Type": "application/json"}
    //             });

    //             const data = await res.json();

    //             if (!res.ok) {
    //                 console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipelines");
    //                 return;
    //             }
    //             console.log("fetch pipelines:", data);
    //             setPipelines(data);

    //         } catch (e) {
    //             console.error("Failed to fetch pipelines:", e);
    //         }
    //     };

    //     if(project) fetchPipelines();
    // }, [project]);

    // persist project and pipeline to stay on after refresh
    // useEffect(() => {
    //     const currentProjectId = sessionStorage.getItem("project_history_id");
    //     const currentPipelineId = sessionStorage.getItem("pipeline_id");

    //     if (currentProjectId) {
    //         const projectId = Number(currentProjectId);
    //         setProject(projects.find(p => p.id === projectId) ?? null);
    //     }

    //     if (currentPipelineId){
    //         const pipelineId = Number(currentPipelineId);
    //         setPipeline(pipelines.find(p => p.id === pipelineId) ?? null);
    //     }
    // }, [projects, pipelines]);

    // make top bar scroll to top on collapsing
    useEffect(()=>{
        if(!isExpanded){
            topContentRef.current?.scrollTo({ top: 0, behavior:"smooth"});
        }
    },[isExpanded]);

    //check top content height to show or hide expand button
    // useEffect(()=>{
    //     const checkOverflow=()=>{
    //         const el=topContentRef.current;
    //         if(!el)return;
    //         const firstChild=el.firstElementChild as HTMLElement | null;
    //         if(!firstChild)return;
    //         const collapsedHeight=firstChild.offsetHeight;
    //         setShowExpandBtn(el.scrollHeight > collapsedHeight + 8);
    //     };

    //     checkOverflow();

    //     window.addEventListener("resize",checkOverflow);
    //     return()=>window.removeEventListener("resize",checkOverflow);
    // },[project,pipeline, isExpanded]);


    return(
        <div className={styles.window}>
            {/* <HProjects projectId={project?.id ?? null} setProject={setProject} projects={projects}/> */}
            <HProjects isEdit={isEdit}/>

            <div className={styles.historyContainer}>
                {project && <div className={`${styles.topBar} ${isExpanded && styles.expanded}`}>
                    <div className={styles.topBarContent} ref={topContentRef}>
                        <Link title="Go to link" 
                            className={`${styles.barTab} ${styles.barLink}`} to={project.repo_url}>
                            {project.repo_url}</Link>
                        <span className={styles.barTab}>{lastSynced ? lastSynced.toLocaleString(): "Never Synced"}</span>

                        {pipeline && <>
                            <span className={styles.barTab}>{pipeline.name}</span>
                            <span className={styles.barTab}>Commit Hash ({pipeline.commit_hash})</span>
                            <span className={styles.barTab}>{pipeline.author}</span>
                            <span className={styles.barTab}>{pipeline.path}</span>
                            <span className={styles.barTab}>{pipeline.is_active?"Published":"Not-Published"}</span>
                            {/* {isExpanded && <> */}
                            <span className={styles.barTab}>Created ({new Date(pipeline.created_at).toLocaleString()})</span>
                            <span className={styles.barTab}>Last Updated ({pipeline.updated_at.toLocaleString()})</span>
                                {pipeline.is_active && 
                                <span className={styles.barTab}>Activated ({pipeline.activated_at.toLocaleString()})</span>}
                            {/* </>} */}
                        </>}
                    </div>
                    <button className={styles.expandBtn} onClick={()=>setIsExpanded(!isExpanded)}>
                        <IoIosArrowDropdownCircle/> </button>
                </div>}
                <div className={styles.historyWindow}>
                    <HistoryBar pipelines={pipelines}
                        // pipelines={pipelines}
                        // pipeline={pipeline}
                        // setPipeline={setPipeline}
                    />
                    {(project && pipeline)?
                        (isEdit ? <PipelineEditor initJobs={jobs} setInitJobs={setJobs}
                            // project={project} pipeline={pipeline} 
                            // setIsEdit={setIsEdit} isDark={isDark} setIsDark={setIsDark} 
                            />
                            :<PipelineViewer jobs={jobs}
                            // project={project} pipeline={pipeline}
                            // setIsEdit={setIsEdit} isDark={isDark} setIsDark={setIsDark} 
                            />
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
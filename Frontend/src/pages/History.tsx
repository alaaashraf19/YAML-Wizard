import gStyles from "../global.module.css"
import styles from './History.module.css'

import HProjects from "../components/History/HProjects";
import type { Pipeline, Project } from "../types";
import { useEffect, useState } from "react";

import { FiFilter } from "react-icons/fi";
import { FaPlus, FaMinus } from "react-icons/fa";


function History(){
    const [project, setProject] = useState<Project | null>(null);
    const [pipelines, setPipelines] = useState<Pipeline[]>([
        // {
        // "id": 0,
        // "name": "string",
        // "path": "string",
        // "branch": "string",
        // "is_active": false,
        // "created_at": "2026-06-25T03:47:51.317Z"
        // },{
        // "id": 0,
        // "name": "string",
        // "path": "string",
        // "branch": "string",
        // "is_active": false,
        // "created_at": "2026-06-25T03:47:51.317Z"
        // },{
        // "id": 0,
        // "name": "string",
        // "path": "string",
        // "branch": "string",
        // "is_active": false,
        // "created_at": "2026-06-25T03:47:51.317Z"
        // }
    ]);

    const api_url = import.meta.env.VITE_API_URL;
    
    //get project pipelines
    useEffect(() => {
        const fetchPipelines = async () => {
            try {
                const res = await fetch(`${api_url}/projects/${project?.id}/pipelines`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch pipelines");
                    return;
                }
                console.log("fetch pipelines:", data);
                setPipelines(data);

            } catch (e) {
                console.error("Failed to fetch pipelines:", e);
            }
        };

        if(project) fetchPipelines();
    }, [project]);

    return(
        <div className={styles.window}>
            <HProjects projectId={project?.id ?? null} setProject={setProject}/>
            <div className={styles.historyWindow}>
                <p className={styles.header}>Version History</p>
                {pipelines.length > 0 ? 
                <div className={styles.namesContainer}>
                    {pipelines.map((pipeline, index) => (
                        <p key={index} className={`${styles.pipelineName} ${gStyles.clickable}`}>{pipeline.name}</p>
                    ))}
                    <FiFilter className={`${styles.filterIcon} ${gStyles.clickable}`} title="Filter"/>
                </div> 
                : <p className={styles.noPipelines}>No pipelines added yet.</p>}
                
            </div>
            <div className={styles.scriptWindow}>
                <div className={styles.editBar}>
                    <div className={styles.divider}></div>
                    <div className={styles.line}>
                        <FaMinus className={`${styles.lineBtn} ${gStyles.clickable}`} title="Down"/>
                        <FaPlus className={`${styles.lineBtn} ${gStyles.clickable}`} title="Up"/>
                    </div>
                </div>
                <div className={styles.pipeline}></div>
            </div>
        </div>
    );
}

export default History;
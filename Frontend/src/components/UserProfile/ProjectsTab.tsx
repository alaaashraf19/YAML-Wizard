import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'

import type { Project, Platform } from "../../types";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

type ProjectsProps = {
    activeTab: string | null,
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>,
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>
};

function ProjectsTab({ activeTab, projects, setProjects, setProjectInfoId, setConfirmMessage, setErrorMessage }: ProjectsProps) {
    const [projectName, setProjectName] = useState<string>('');
    const [repoURL, setRepoUrl] = useState<string>('');
    const [targetPlatform, setTargetPlatform] = useState<Platform>('github' as Platform);

    const api_url = import.meta.env.VITE_API_URL;
    const navigate = useNavigate();

    // sort sessions 
    const projectsSorted = useMemo(() => {
        return [...projects].sort((a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )}, [projects]);
    
    //get user projects
    useEffect(() => {
        const fetchProjects = async () => {
            try {
                const res = await fetch(`${api_url}/projects`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to load projects");
                    return;
                }
                setProjects(data);

            } catch (e) {
                console.error("Failed to load projects:", e);
            }
        };

        fetchProjects();
    }, []);

    // add new project
    const handleAddProject = async (e: React.FormEvent) => {
        e.preventDefault();
        const error = validateProjectAdd();
        if (error) {
            setErrorMessage(error);
            return;
        }
        setErrorMessage("");

        try{
            const res = await fetch(`${api_url}/projects`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    "project_name": projectName,
                    "url": repoURL
                    }
                )
            });

            const data = await res.json();

            if(!res.ok){
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to add project");
                setErrorMessage(data.detail?.[0]?.msg || data.detail || "Failed to add project");
                return;
            }

            const newProject: Project = data;
            setProjects((prevProjects) => [...prevProjects, newProject]);

            setConfirmMessage("Project " + projectName + " added successfully");

            setProjectName("");
            setRepoUrl("");
            setTargetPlatform("github" as Platform);

        }catch (e: any){
            console.error("Failed to add project:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorMessage(msg);
        }
    };
    const validateProjectAdd = () : string | null => {
        if(!projectName || !repoURL || !targetPlatform){
            return "Some required fields are missing";
        }
        return null;
    };


    return(<>
            {activeTab &&
                <form className={styles.form} onSubmit={
                        (e) => {handleAddProject(e);
                    }}>

                    <h1 className={styles.header}>Add new project</h1>
                    <div className={styles.field}>
                        <label id='project_name' className={styles.fieldLabel}>
                            <span className={styles.labelText}>Project name:</span>
                            <input name='project_name' type="text" placeholder="Enter project name.." value={projectName}
                                className={styles.input} onChange={(e) => setProjectName(e.target.value)}/>
                        </label>
                    </div>

                    <div className={styles.field}>
                        <label id='repo_url' className={styles.fieldLabel}>
                            <span className={styles.labelText}>Repository URL:</span>
                            <input name='repo_url' type="text" placeholder="Enter repository URL .." value={repoURL}
                                className={styles.input} onChange={(e) => setRepoUrl(e.target.value)}/>
                        </label>
                    </div>

                    {/* <div className={styles.field}>
                        <label id="platform_label" className={styles.fieldLabel}>
                            <span className={styles.labelText}>Platform:</span>
                            {Platforms.map((platform, index) => (
                                <label key={index} htmlFor={platform} className={`${gStyles.clickable} ${styles.radio}`}>
                                    <input type="radio" id={platform} name="platform" checked={targetPlatform === platform}
                                        onChange={() => setTargetPlatform(platform as Platform)}/>
                                    <span>{platform.toUpperCase()}</span>
                                </label>
                            ))}
                        </label>
                    </div> */}

                    <button type="submit" className={`${gStyles.clickable} ${styles.button}`}>Add Project</button>
                </form>
            }

            <h1 className={styles.header}>Your Projects</h1>
            {(projects.length > 0) ? (
                <ul className={styles.projectList}>
                    {projectsSorted.map((project, index) => (
                        <li key={index} className={styles.projectItem} title="View project details">
                            <span className={`${styles.projectName} ${gStyles.clickable}`}
                                onClick={() => setProjectInfoId(project.id)}>{project.project_name}</span>
                            <span className={styles.subInfo}>{project.platform}</span>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className={styles.noProjects}>No projects added yet.</p>
            )}

            {!activeTab &&
                <button className={`${gStyles.clickable} ${styles.button}`}
                    onClick={() => navigate(`/profile?tab=Projects`)}>Add Project</button>}
    </>);
}

export default ProjectsTab;
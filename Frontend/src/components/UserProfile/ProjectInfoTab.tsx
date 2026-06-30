import gStyles from "../../global.module.css"
import popupStyles from '../Popup/Popup.module.css'
import styles from './Tabs.module.css'

import Popup from "../Popup/Popup";
import type { Project, Platform, Session } from "../../types";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { IoClose, IoNavigate  } from "react-icons/io5";
import { MdEdit } from "react-icons/md";
import { MdDeleteOutline } from "react-icons/md";


type ProjectInfoTabProps = {
    projectInfoId: number | null,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>,
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>,
    infoRef: React.Ref<HTMLDivElement>,
    popupRef: React.Ref<HTMLDivElement>
}

function ProjectInfoTab({ projectInfoId, setProjectInfoId, projects, setProjects, infoRef, popupRef } : ProjectInfoTabProps){
    const [projectName, setProjectName] = useState<string | undefined>('');
    const [repoURL, setRepoUrl] = useState<string | undefined>('');
    const [platform, setPlatform] = useState<Platform | null | undefined>('github' as Platform);
    const [sessions, setSessions] = useState<Session[]>([]);
    
    const [errorEdit, setErrorEdit] = useState<string | null>("");
    const [editMode, setEditMode] = useState<boolean>(false);
    const [selectedProject, setSelectedProject] = useState<Project>();
    const [askDelete, setAskDelete] = useState<string | null>("");
    
    const localPopupRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    // check if project info id is selected
    useEffect(() => {
        const projectId = sessionStorage.getItem("project_id");

        if(projectId){
            setProjectInfoId(Number(projectId));
            setSelectedProject(projects.find(p => p.id === Number(projectId)));
        }
    }, [projects]);

    // get selected project and its sessions on project-id change
    useEffect(() => {
        const getSessionsOfProject = async () => {
            try {
                const res = await fetch(`${api_url}/projects/${projectInfoId}/sessions`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to load sessions");
                    return;
                }
                setSessions(data);

            } catch (e) {
                console.error("Failed to load sessions:", e);
            }
        }

        if(projectInfoId){
            setSelectedProject(projects.find(p => p.id === projectInfoId));
            getSessionsOfProject();
        }
    }, [projectInfoId]);

    //sort sessions
    const sortedSessions = useMemo(() => {
        return sessions ? sessions
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [sessions]);

    //handle delete a project
    const handleDelete = async () => {
        try{
            const res = await fetch(`${api_url}/projects/${projectInfoId}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }

            setProjects(prev => prev.filter(p => p.id !== projectInfoId));
            setProjectInfoId(null);

        } catch(e) {
            console.log("Failed to delete project:" ,e);
        }
    };

    //handle edit project info
    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();

        const error = validateEdit();
        if (error) {
            setErrorEdit(error);
            return;
        }
        setErrorEdit("");

        try{
            const res = await fetch(`${api_url}/projects/${projectInfoId}`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    "project_name": projectName,
                    "repo_url": repoURL
                    }
                )
            });

            const data = await res.json();

            if(!res.ok){
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to edit project");
                setErrorEdit(data.detail?.[0]?.msg || data.detail || "Failed to edit project");
                return;
            }

            const updatedAt = new Date().toISOString();
            setProjects(projects.map(p => 
                p.id === projectInfoId? {
                    ...p,
                    "project_name": projectName ?? "",
                    "repo_url": repoURL ?? "",
                    "platform": platform ?? "github" as Platform,
                    "updated_at": updatedAt
                } : p
            ));
            setSelectedProject(p => p?
                {
                ...p,
                "project_name": projectName ?? "",
                "repo_url": repoURL ?? "",
                "platform": platform ?? "github" as Platform,
                "updated_at": updatedAt
                } : p
            );

            setEditMode(false);
            
        }catch (e: any){
            console.error("Failed to edit project:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorEdit(msg);
        }
    };
    const validateEdit = (): string | null => {
        if(!projectName || !repoURL){
            return "Some required fields are missing";
        }

        if(projectName === selectedProject?.project_name && 
            repoURL === selectedProject?.repo_url &&
            platform === selectedProject?.platform
        ){
            return "No Change Detected";
        }

        return null;
    };

    return(
        <div className={popupStyles.popupLayover}>
            {askDelete? 
                <Popup
                    btnText1={"Delete"}
                    btn1Action={handleDelete}
                    btnText2={"Cancel"}
                    questionMessage={askDelete}
                    setQuestionMessage={setAskDelete}
                    popupRef={popupRef}
                />
                : <div className={`${styles.infoPopup} ${popupStyles.popup}`} ref={editMode? null : infoRef}>
                {editMode? (<>
                    <div className={styles.infoBtns}>
                            <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}
                                onClick={() => setEditMode(false)} title="Discard edit"/>
                    </div>

                    <form className={`${styles.form} ${styles.infoForm}`} onSubmit={
                            (e) => {handleEdit(e);
                        }}>
                        <div className={`${styles.field} ${styles.editField}`}>
                            <label id='project_name' className={styles.fieldLabel}>
                                <span className={styles.labelText}>Project name:</span>
                                <input name='project_name' type="text" placeholder="Enter project name.." value={projectName}
                                    className={styles.input} onChange={(e) => setProjectName(e.target.value)}/>
                            </label>
                        </div>
                        <div className={`${styles.field} ${styles.editField}`}>
                            <label id='repo_url' className={styles.fieldLabel}>
                                <span className={styles.labelText}>Repository URL:</span>
                                <input name='repo_url' type="text" placeholder="Enter repo url.." value={repoURL}
                                    className={styles.input} onChange={(e) => setRepoUrl(e.target.value)}/>
                            </label>
                        </div>

                        {/* <div className={`${styles.field} ${styles.editField}`}>
                            <label id="platform_label" className={styles.fieldLabel}>
                                <span className={styles.labelText}>Platform:</span>
                                {Platforms.map((platform, index) => (
                                    <label key={index} htmlFor={platform} className={`${gStyles.clickable} ${styles.radio}`}>
                                        <input type="radio" id={platform} name="platform" checked={platform === platform}
                                            onChange={() => setPlatform(platform as Platform)}/>
                                        <span>{platform.toUpperCase()}</span>
                                    </label>
                                ))}
                            </label>
                        </div> */}

                        <button type="submit" title="Confirm Edit"
                            className={`${gStyles.gButton} ${styles.button} ${styles.editBtn}`}>
                            Edit
                        </button>
                    </form>

                    {errorEdit && (
                        <Popup 
                            btnText1={"Got it"}
                            errorMessage={errorEdit}
                            setErrorMessage={setErrorEdit}
                            popupRef={localPopupRef}
                        />
                    )}
                </>) : (<>
                    <div className={styles.infoBtns}>
                        <MdDeleteOutline className={`${gStyles.clickable} ${styles.infoBtn}`} title="Delete Project"
                            onClick={() => setAskDelete("Delete project '" + selectedProject?.project_name + "' ?")}/>
                        <MdEdit className={`${gStyles.clickable} ${styles.infoBtn}`} title="Edit Info" 
                            onClick={() => {
                                setEditMode(true);
                                setProjectName(selectedProject?.project_name);
                                setRepoUrl(selectedProject?.repo_url);
                                setPlatform(selectedProject?.platform);
                        }}/>
                        <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}  title="Close Info"
                            onClick={() => {
                                setProjectInfoId(null);
                                sessionStorage.removeItem("project_id");
                            }}/>
                    </div>

                    <ProjectSubInfo selectedProject={selectedProject}/>
                    
                    <div className={`${styles.infoBar} ${styles.infoBarSessions}`}>
                        <p className={styles.infoLabel}>Connected Sessions</p>
                        {sortedSessions.length > 0 ? (
                        <div className={styles.sessions}>
                            {sortedSessions.map((session, index) => (
                                <div key={index} className={styles.session}>
                                    <span>{session.session_name}</span>
                                    <span className={`${styles.navigateIcon} ${gStyles.clickable}`}
                                            title="Go to session" onClick={() => {
                                                if(session.id) sessionStorage.setItem("session_id", session.id.toString());
                                                else sessionStorage.removeItem("session_id");
                                                navigate("/chatbot");
                                            }}> <IoNavigate/> </span>
                                </div>
                            ))}
                        </div>
                        ) : (
                            <p className={styles.noProjects}>No connected sessions yet.</p>
                        )}
                    </div>
                </>)}
            </div>
            }
        </div>
        
    );
}

export default ProjectInfoTab;

type subProps = {
    selectedProject: Project | null | undefined
}
export function ProjectSubInfo({ selectedProject }:subProps){
    const loadingText = "Getting Information ..";

    return(<>
        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Project Name</p>
            <p className={styles.infoText}>{selectedProject?.project_name ?? loadingText}</p>
        </div>
        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Repository URL</p>
            {selectedProject?.repo_url ? 
            <a href={selectedProject?.repo_url} className={styles.link}
                title="Go to repo">{selectedProject?.repo_url}</a>
            : <p className={styles.infoText}>{loadingText}</p>}
        </div>
        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Platform</p>
            <p className={styles.infoText}>{selectedProject?.platform?.toUpperCase() ?? loadingText}</p>
        </div>
        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Branch</p>
            <p className={styles.infoText}>{selectedProject?.branch?.toUpperCase() ?? loadingText}</p>
        </div>

        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Created</p>
            <p className={styles.infoText}>
                {selectedProject?.created_at ?
                    new Date(selectedProject.created_at).toLocaleString(): loadingText}</p>
        </div>
        <div className={styles.infoBar}>
            <p className={styles.infoLabel}>Last Updated</p>
            <p className={styles.infoText}>
                {selectedProject?.updated_at ?
                    new Date(selectedProject.updated_at).toLocaleString(): loadingText}</p>
        </div>
    </>);
}
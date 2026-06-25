import gStyles from "../../global.module.css"
import popupStyles from '../Popup/Popup.module.css'
import styles from './Tabs.module.css'

import type { Project, Platform } from "../../types";
import { Platforms } from "../../types";
import { Popup } from "../Popup/Popup";
import { useEffect, useRef, useState } from "react";

import { IoClose } from "react-icons/io5";
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

function ProjectInfoTab(PITProps : ProjectInfoTabProps){
    const [projectName, setProjectName] = useState<string | undefined>('');
    const [repoURL, setRepoUrl] = useState<string | undefined>('');
    const [platform, setPlatform] = useState<Platform | null | undefined>('github' as Platform);
    
    const [errorEdit, setErrorEdit] = useState<string | null>("");
    const [editMode, setEditMode] = useState<boolean>(false);
    const [selectedProject, setSelectedProject] = useState<Project>();
    const [confirmDelete, setConfirmDelete] = useState<string | null>("");
    
    const popupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;

    // get selected project on project-id change
    useEffect(() => {
        if(PITProps.projectInfoId){
            setSelectedProject(PITProps.projects.find(p => p.id === PITProps.projectInfoId));
        }
    }, [PITProps.projectInfoId]);

    //handle delete a project
    const handleDelete = async () => {
        try{
            const res = await fetch(`${api_url}/projects/${PITProps.projectInfoId}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }

            PITProps.setProjects(prev => prev.filter(p => p.id !== PITProps.projectInfoId));
            PITProps.setProjectInfoId(null);

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
            const res = await fetch(`${api_url}/projects/${PITProps.projectInfoId}`, {
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
            PITProps.setProjects(PITProps.projects.map(p => 
                p.id === PITProps.projectInfoId? {
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
            {confirmDelete? 
                <Popup
                    btnText1={"Delete"}
                    btn1Action={handleDelete}
                    btnText2={"Cancel"}
                    btn2Action={null}
                    confirmMessage={confirmDelete}
                    setConfirmMessage={setConfirmDelete}
                    warningMessage={null}
                    setWarningMessage={null}
                    errorMessage={null}
                    setErrorMessage={null}
                    popupRef={PITProps.popupRef}
                />
                : <div className={`${styles.infoPopup} ${popupStyles.popup}`} ref={editMode? null : PITProps.infoRef}>
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
                            className={`${gStyles.clickable} ${styles.button} ${styles.editBtn}`}>
                            Edit
                        </button>
                    </form>

                    {errorEdit && (
                        <Popup 
                            btnText1={"Got it"}
                            btn1Action={null}
                            btnText2={null}
                            btn2Action={null}
                            confirmMessage={null}
                            setConfirmMessage={null}
                            warningMessage={null}
                            setWarningMessage={null}
                            errorMessage={errorEdit}
                            setErrorMessage={setErrorEdit}
                            popupRef={popupRef}
                        />
                    )}
                </>) : (<>
                    <div className={styles.infoBtns}>
                        <MdDeleteOutline className={`${gStyles.clickable} ${styles.infoBtn}`} title="Delete Project"
                            onClick={() => setConfirmDelete("Delete the project '" + selectedProject?.project_name + "' ?")}/>
                        <MdEdit className={`${gStyles.clickable} ${styles.infoBtn}`} title="Edit Info" 
                            onClick={() => {
                                setEditMode(true);
                                setProjectName(selectedProject?.project_name);
                                setRepoUrl(selectedProject?.repo_url);
                                setPlatform(selectedProject?.platform);
                        }}/>
                        <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}
                            onClick={() => PITProps.setProjectInfoId(null)} title="Close Info"/>
                    </div>
                    <div className={styles.infoBar}>
                        <p className={styles.infoLabel}>Project Name</p>
                        <p className={styles.infoText}>{selectedProject?.project_name}</p>
                    </div>
                    <div className={styles.infoBar}>
                        <p className={styles.infoLabel}>Repository URL</p>
                        <a href={selectedProject?.repo_url} className={styles.link}
                            title="Go to repo">{selectedProject?.repo_url}</a>
                    </div>
                    <div className={styles.infoBar}>
                        <p className={styles.infoLabel}>Platform</p>
                        <p className={styles.infoText}>{selectedProject?.platform}</p>
                    </div>
                </>)}

                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Created</p>
                    <p className={styles.infoText}>{new Date(selectedProject?.created_at??"").toLocaleString()}</p>
                </div>
                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Last Updated</p>
                    <p className={styles.infoText}>{new Date(selectedProject?.updated_at??"").toLocaleString()}</p>
                </div>
                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Connected Sessions</p>
                </div>
            </div>
            }
        </div>
        
    );
}

export default ProjectInfoTab;
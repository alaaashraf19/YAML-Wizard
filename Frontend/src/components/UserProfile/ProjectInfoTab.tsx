import gStyles from "../../global.module.css"
import popupStyles from '../Popup/Popup.module.css'
import styles from './Tabs.module.css'

import type { Project, Platform } from "../../types";
import { Popup } from "../Popup/Popup";
import { useRef, useState } from "react";

import { IoClose } from "react-icons/io5";
import { MdEdit } from "react-icons/md";
import { MdDeleteOutline } from "react-icons/md";


type ProjectInfoTabProps = {
    projectInfoId: number | null,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>,
    selectedProject: Project | undefined,
    setSelectedProject: React.Dispatch<React.SetStateAction<Project | undefined>>,
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>,
    infoRef: React.Ref<HTMLDivElement>,
    setConfirmDelete: React.Dispatch<React.SetStateAction<string | null>>
}

export function ProjectInfoTab(PITProps : ProjectInfoTabProps){

    const [projectName, setProjectName] = useState<string | undefined>('');
    const [repoURL, setRepoUrl] = useState<string | undefined>('');
    const [targetPlatform, setTargetPlatform] = useState<Platform | null | undefined>('github' as Platform);
    
    const [errorEdit, setErrorEdit] = useState<string | null>("");
    const [editMode, setEditMode] = useState<boolean>(false);
    
    const popupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;

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
                method: "Put",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    "project_name": projectName,
                    "repo_url": repoURL,
                    "target_platform": targetPlatform
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
                    "target_platform": targetPlatform ?? "github" as Platform,
                    "updated_at": updatedAt
                } : p
            ));
            PITProps.setSelectedProject(p => p?
                {
                ...p,
                "project_name": projectName ?? "",
                "repo_url": repoURL ?? "",
                "target_platform": targetPlatform ?? "github" as Platform,
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

        if(projectName === PITProps.selectedProject?.project_name && 
            repoURL === PITProps.selectedProject?.repo_url &&
            targetPlatform === PITProps.selectedProject?.target_platform
        ){
            return "No Change Detected";
        }

        return null;
    };

    return(
        <div className={`${styles.infoPopup} ${popupStyles.popup}`} ref={editMode? null : PITProps.infoRef}>
            {editMode? (<>
                <div className={styles.infoBtns}>
                        <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}
                            onClick={() => setEditMode(false)} title="Discard edit"/>
                </div>
                <form className={styles.section} onSubmit={
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

                    <div className={`${styles.field} ${styles.editField}`}>
                        <label id="platform_label" className={styles.fieldLabel}>
                            <span className={styles.labelText}>Platform:</span>
                            <label htmlFor="github" className={`${gStyles.clickable} ${styles.radio}`}>
                                <input type="radio" id="github" name="platform" checked={targetPlatform === "github"}
                                    onChange={() => setTargetPlatform('github' as Platform)}/>
                                <span>GitHub</span>
                            </label>

                            <label htmlFor="gitlab" className={`${gStyles.clickable} ${styles.radio}`}>
                                <input type="radio" id="gitlab" name="platform" checked={targetPlatform === "gitlab"}
                                    onChange={() => setTargetPlatform('gitlab' as Platform)}/>
                                <span>GitLab</span>
                            </label>
                        </label>
                    </div>

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
                        onClick={() => PITProps.setConfirmDelete("Delete the project '" + PITProps.selectedProject?.project_name + "' ?")}/>
                    <MdEdit className={`${gStyles.clickable} ${styles.infoBtn}`} title="Edit Info" 
                        onClick={() => {
                            setEditMode(true);
                            setProjectName(PITProps.selectedProject?.project_name);
                            setRepoUrl(PITProps.selectedProject?.repo_url);
                            setTargetPlatform(PITProps.selectedProject?.target_platform);
                    }}/>
                    <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}
                        onClick={() => PITProps.setProjectInfoId(null)} title="Close Info"/>
                </div>
                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Project Name</p>
                    <p className={styles.infoText}>{PITProps.selectedProject?.project_name}</p>
                </div>
                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Repository URL</p>
                    <p className={styles.infoText}>{PITProps.selectedProject?.repo_url}</p>
                </div>
                <div className={styles.infoBar}>
                    <p className={styles.infoLabel}>Platform</p>
                    <p className={styles.infoText}>{PITProps.selectedProject?.target_platform}</p>
                </div>
            </>)}

            <div className={styles.infoBar}>
                <p className={styles.infoLabel}>Created</p>
                <p className={styles.infoText}>{new Date(PITProps.selectedProject?.created_at??"").toLocaleString()}</p>
            </div>
            <div className={styles.infoBar}>
                <p className={styles.infoLabel}>Last Updated</p>
                <p className={styles.infoText}>{new Date(PITProps.selectedProject?.updated_at??"").toLocaleString()}</p>
            </div>
            <div className={styles.infoBar}>
                <p className={styles.infoLabel}>Connected Sessions</p>
            </div>
        </div>
    );
}
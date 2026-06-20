import gStyles from "../../global.module.css"
import popupStyles from '../Popup/Popup.module.css'
import styles from './Tabs.module.css'
import { Popup } from "../Popup/Popup";
import { ProjectInfoTab } from "./ProjectInfoTab"
import { UsernameField, EmailField, PasswordField } from "../AuthForm/AuthForm";
import type { Project, Platform } from "../../types";
import { useEffect, useMemo, useState } from "react";

type ProfileProps = {
    username: string,
    email: string,
    setUsername: React.Dispatch<React.SetStateAction<string>>,
    setEmail: React.Dispatch<React.SetStateAction<string>>,
    handleUpdateProfile: (e: React.FormEvent) => void
};

export function ProfileTab({ username, email, setUsername, setEmail, handleUpdateProfile }: ProfileProps) {
    const [editUsername, setEditUsername] = useState<boolean>(false);
    const [editEmail, setEditEmail] = useState<boolean>(false);
    return (
        <form className={styles.section}
            onSubmit={(e) => {handleUpdateProfile(e); setEditUsername(false); setEditEmail(false);}}>
            <h1 className={styles.header}>Profile</h1>
            <UsernameField
                username={username}
                setUsername={setUsername}
                editUsername={editUsername}
                setEditUsername={setEditUsername}
                />
            <EmailField
                email={email}
                setEmail={setEmail}
                editEmail={editEmail}
                setEditEmail={setEditEmail}
                />
            {(editUsername || editEmail) && 
                <button type="submit" className={`${gStyles.clickable} ${styles.button}`}>
                    Update Profile
                </button>
            }
        </form>
    );
}

type SecurityProps = {
    password: string,
    newPassword: string,
    confirmPassword: string,
    showPassword: boolean,
    showNewPassword: boolean,
    showConfirmPassword: boolean,
    setPassword: React.Dispatch<React.SetStateAction<string>>,
    setNewPassword: React.Dispatch<React.SetStateAction<string>>,
    setConfirmPassword: React.Dispatch<React.SetStateAction<string>>,
    setShowPassword: React.Dispatch<React.SetStateAction<boolean>>,
    setShowNewPassword: React.Dispatch<React.SetStateAction<boolean>>,
    setShowConfirmPassword: React.Dispatch<React.SetStateAction<boolean>>,
    handleSubmitNewPassword: (e: React.FormEvent) => void
};

export function SecurityTab({
        password,
        newPassword,
        confirmPassword,
        showPassword,
        showNewPassword,
        showConfirmPassword,
        setPassword,
        setNewPassword,
        setConfirmPassword,
        setShowPassword,
        setShowNewPassword,
        setShowConfirmPassword,
        handleSubmitNewPassword
    }: SecurityProps) {

    return (
        <form className={styles.section} onSubmit={(e) => {handleSubmitNewPassword(e);}}>
            <h1 className={styles.header}>Security</h1>
            <PasswordField 
                type="Current Password"
                password={password}
                setPassword={setPassword}
                showPassword={showPassword}
                setShowPassword={setShowPassword}
            />
            <PasswordField 
                type="New Password"
                password={newPassword}
                setPassword={setNewPassword}
                showPassword={showNewPassword}
                setShowPassword={setShowNewPassword}
            />
            <PasswordField
                type="Confirm Password"
                password={confirmPassword}
                setPassword={setConfirmPassword}
                showPassword={showConfirmPassword}
                setShowPassword={setShowConfirmPassword}
            />
            <button type="submit" className={`${gStyles.clickable} ${styles.button}`}>Change Password</button>
        </form>
    );
}

type ProjectsProps = {
    projects: Project[],
    projectName: string,
    setProjectName: React.Dispatch<React.SetStateAction<string>>,
    repoURL: string,
    setRepoUrl: React.Dispatch<React.SetStateAction<string>>,
    targetPlatform: string,
    setTargetPlatform: React.Dispatch<React.SetStateAction<Platform>>,
    handleSubmitProject: (e: React.FormEvent) => void,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>
};

export function ProjectsTab({
        projects,
        projectName,
        setProjectName,
        repoURL,
        setRepoUrl,
        targetPlatform,
        setTargetPlatform,
        handleSubmitProject,
        setProjectInfoId
    }: ProjectsProps) {

    // sort sessions 
    const projectsSorted = useMemo(() => {
        return [...projects].sort((a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )}, [projects]);

    return(<>
            <h1 className={styles.header}>Added Projects</h1>
            {(projects.length > 0) ? (
                <ul className={styles.projectList}>
                    {projectsSorted.map((project, index) => (
                        <li key={index} className={`${styles.projectItem} ${gStyles.clickable}`}
                            title="View project details" onClick={() => setProjectInfoId(project.id)}>
                            {project.project_name}
                        </li>
                    ))}
                </ul>
            ) : (
                <p className={styles.noProjects}>No projects added yet.</p>
            )}

            <form className={styles.section} onSubmit={
                    (e) => {handleSubmitProject(e);
                }}>

                <h1 className={styles.header}>Add a new project</h1>
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

                <div className={styles.field}>
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

                <button type="submit" className={`${gStyles.clickable} ${styles.button}`}>Add Project</button>
            </form>
    </>);
}

type ProjectInfoProps = {
    projectInfoId: number | null,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>,
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>,
    infoRef: React.Ref<HTMLDivElement>,
    popupRef: React.Ref<HTMLDivElement>
}

export function ProjectInfo(PIProps: ProjectInfoProps){
    const [selectedProject, setSelectedProject] = useState<Project>();
    const [confirmDelete, setConfirmDelete] = useState<string | null>("");

    const api_url = import.meta.env.VITE_API_URL;
    
    // get selected project on project-id change
    useEffect(() => {
        if(PIProps.projectInfoId){
            setSelectedProject(PIProps.projects.find(p => p.id === PIProps.projectInfoId));
        }
    }, [PIProps.projectInfoId]);

    //handle delete a project
    const handleDelete = async () => {
        try{
            const res = await fetch(`${api_url}/projects/${PIProps.projectInfoId}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }

            PIProps.setProjects(prev => prev.filter(p => p.id !== PIProps.projectInfoId));
            PIProps.setProjectInfoId(null);

        } catch(e) {
            console.log("Failed to delete project:" ,e);
        }
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
                    popupRef={PIProps.popupRef}
                />
                : <ProjectInfoTab
                    projectInfoId={PIProps.projectInfoId}
                    setProjectInfoId={PIProps.setProjectInfoId}
                    selectedProject={selectedProject}
                    setSelectedProject={setSelectedProject}
                    projects={PIProps.projects}
                    setProjects={PIProps.setProjects}
                    infoRef={PIProps.infoRef}
                    setConfirmDelete={setConfirmDelete}
                />
            }
        </div>
    );
}

type PlatformProps = {
    handleConnectGithub: () => void,
    handleConnectGitlab: () => void,
    handleInstallApp: () => void

}

export function PlatformsTab({ handleConnectGithub, handleConnectGitlab, handleInstallApp }: PlatformProps){
    return(
        <div className={styles.section}>
            <h1 className={styles.header}>Platforms</h1>
            <h2>GitHub</h2>
            <button onClick={handleConnectGithub} className={`${gStyles.clickable} ${styles.button}`}>
                Connect with github account
            </button>
            <button onClick={handleInstallApp} className={`${gStyles.clickable} ${styles.button}`}>
                Install app
            </button> 

            <h2>GitLab</h2>
            <button onClick={handleConnectGitlab} className={`${gStyles.clickable} ${styles.button}`}>
                Connect with gitlab account
            </button>

        </div>
    );
}
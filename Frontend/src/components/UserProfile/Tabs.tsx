import gStyles from "../../global.module.css"
import popupStyles from '../Popup/Popup.module.css'
import styles from './Tabs.module.css'
import { Popup } from "../Popup/Popup";
import { ProjectInfo } from "./ProjectInfo"
import { UsernameField, EmailField, PasswordField } from "../AuthForm/AuthForm";
import type { Project, Platform } from "../../types";
import { Platforms } from "../../types";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { GoPerson } from "react-icons/go";

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
    const [profilePicture, setProfilePicture] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string>();

    useEffect(() => {
        if (!profilePicture) return;

        const url = URL.createObjectURL(profilePicture);
        setPreviewUrl(url);

        return () => URL.revokeObjectURL(url);
    }, [profilePicture]);

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            setProfilePicture(e.target.files[0]);
        }
    };

    return (<>
        <h1 className={styles.header}>Profile</h1>
        <div className={styles.profile}>
            <form className={`${styles.section} ${styles.profileSection}`}
                onSubmit={(e) => {handleUpdateProfile(e); setEditUsername(false); setEditEmail(false);}}>
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
            <div className={styles.imgContainer}>
                {previewUrl ? 
                <img className={styles.img} src={previewUrl} alt="Profile"/>
                :
                <GoPerson className={styles.img}/>
                }

                <div className={styles.imgBtnContainer}>
                    <label htmlFor="fileInput"
                        className={`${styles.inputImg} ${styles.button}  ${gStyles.clickable}`}>
                        Change Image
                    </label>
                    <input type="file" id="fileInput" accept="image/*" onChange={handleImageChange}
                        hidden/>
                </div>
            </div>
        </div>
    </>);
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
    activeTab: string | null,
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
        activeTab,
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

    const navigate = useNavigate();
    // sort sessions 
    const projectsSorted = useMemo(() => {
        return [...projects].sort((a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )}, [projects]);

    return(<>
            {activeTab &&
                <form className={styles.section} onSubmit={
                        (e) => {handleSubmitProject(e);
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

                    <div className={styles.field}>
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
                    </div>

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
                            <span className={styles.platformName}>{project.target_platform}</span>
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

type ProjectInfoProps = {
    projectInfoId: number | null,
    setProjectInfoId: React.Dispatch<React.SetStateAction<number | null>>,
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>,
    infoRef: React.Ref<HTMLDivElement>,
    popupRef: React.Ref<HTMLDivElement>
}

export function ProjectInfoTab(PIProps: ProjectInfoProps){
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
                : <ProjectInfo
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

type PlatformConnection = {
    connected: boolean;
    username: string | null;
};
type Repo = {
    name: string;
    url: string;
};

type PlatformsProps = {
    popupRef: React.Ref<HTMLDivElement>
};

export function PlatformsTab({ popupRef }: PlatformsProps){
    const [connections, setConnections] = useState<Partial<Record<Platform, PlatformConnection>>>({});
    const [repos, setRepos] = useState<Repo[]>([]);
    const [confirmMessage, setConfirmMessage] = useState<string | null>("");
    const [errorMessage, setErrorMessage] = useState<string | null>("");
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const api_url = import.meta.env.VITE_API_URL;

    //check for connection to show popup
    useEffect(() => {
        const platform = Platforms.find(p => searchParams.get(p) !== null);

        if (!platform) return;

        const connectionStatus = searchParams.get(platform);
        const reason = searchParams.get("reason");

        if (connectionStatus === "success") {
            setConfirmMessage(`${platform.toUpperCase()} connected successfully`);
        }

        if (connectionStatus === "error") {
            setErrorMessage(reason ?? `Failed to connect ${platform}.`);
        }
    }, [searchParams]);

    //check connected or not
    useEffect(() => {
        const checkConnected = async () => {
            try {
                const res = await fetch(`${api_url}/platform/integration/status`, {
                    credentials: "include"
                });

                const data = await res.json();

                if (!res.ok) {
                    console.log("Error:", data.detail);
                    setConnections({});
                    return;
                }

                setConnections(data);

            } catch (err) {
                console.error("Server error:", err);
                setConnections({});
            }
        };

        checkConnected();
    }, []);
    
    //get installed repos
    useEffect(() => {
        const getInstalled = async () => {
            try {
                const res = await fetch(`${api_url}/github/installations/repos`, {
                    credentials: "include"
                });

                const data = await res.json();

                if (!res.ok) {
                    console.log("Error:", data.detail);
                    setRepos([]);
                    return;
                }

                setRepos(data.map((r: any) => ({
                    name: r.repo_full_name,
                    url: r.repo_url
                })));

            } catch (err) {
                console.error("Server error:", err);
                setRepos([]);
            }
        };

        getInstalled();
    }, []);

    const handleConnectPlatfrom = (platform: Platform) => {
        setIsLoading(true);
        setTimeout(() => {
            window.location.href = `${api_url}/platform/${platform.toLowerCase()}/connect`;
        }, 100);
    };

    const handleInstallApp = () => {
        setIsLoading(true);
        setTimeout(() => {
            window.location.assign(`${api_url}/github/install_app`);
        }, 100);
    };

    return(
        <div className={styles.section}>
            <h1 className={styles.header}>Platforms</h1>

            {Platforms.map((platfrom, index) => (
                <div key={index} className={styles.platform}>
                    <h2>{platfrom.toUpperCase()}</h2>

                    {connections[platfrom]?.connected ? (
                        <div className={styles.pSection}>
                            <label>Username:</label>
                            <p>{connections[platfrom]?.username}</p>
                        </div>
                    ) : (
                        <button onClick={() => handleConnectPlatfrom(platfrom)}
                            className={`${gStyles.clickable} ${styles.button}`}>
                            {isLoading ? "Redirecting .." :`Connect with ${platfrom} account`}
                        </button>
                    )}

                    {platfrom === "github" &&
                        <div className={styles.pSection}>
                            <label>Connected Repositories:</label>
                            <ul>
                                {repos.length > 0 ? (
                                    repos.map((repo, index) => (
                                        <li key={index} className={styles.item} title="Go to repo">
                                            <Link to={repo.url} className={styles.link}>
                                                {repo.name}</Link>
                                        </li>
                                    ))
                                ) : (
                                    <p className={styles.noProjects}>No repos added yet.</p>
                                )}
                            </ul>
                            <button onClick={handleInstallApp} className={`${gStyles.clickable} ${styles.button}`}
                                title="Install app to add more repositories" disabled={isLoading}>
                                {isLoading ? "Redirecting .." :"Install App"}
                            </button>
                        </div>
                    }
                </div>
            ))}

            {(errorMessage || confirmMessage) && 
                <Popup 
                    btnText1={"Got it"}
                    btn1Action={() => {navigate("/profile", { replace: true });}}
                    btnText2={null}
                    btn2Action={null}
                    confirmMessage={confirmMessage}
                    setConfirmMessage={setConfirmMessage}
                    warningMessage={null}
                    setWarningMessage={null}
                    errorMessage={errorMessage}
                    setErrorMessage={setErrorMessage}
                    popupRef={popupRef}
                />
            }
        </div>
    );
}
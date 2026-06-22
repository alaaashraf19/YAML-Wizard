import gStyles from "../global.module.css"
import styles from './UserProfile.module.css'
import type { Project, Platform } from "../types";
import { ProfileTab, SecurityTab, ProjectsTab, PlatformsTab, ProjectInfo } from "../components/UserProfile/Tabs";
import { Popup } from "../components/Popup/Popup"
import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";


const tabs = ["Profile", "Security", "Projects", "Platforms"];

function UserProfile() {
    const [searchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState<string | null>(searchParams.get("tab") || null);
    
    //fields
    const [currUsername, setCurrUsername] = useState("");
    const [username, setUsername] = useState("");
    const [currEmail, setCurrEmail] = useState("");
    const [email, setEmail] = useState("");

    const [password, setPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    
    const [projectName, setProjectName] = useState<string>('');
    const [repoURL, setRepoUrl] = useState<string>('');
    const [targetPlatform, setTargetPlatform] = useState<Platform>('github' as Platform);
    const [projects, setProjects] = useState<Project[]>([]);
    const [projectInfoId, setProjectInfoId] = useState<number | null>(null);

    const [confirmMessage, setConfirmMessage] = useState<string | null>("");
    const [errorMessage, setErrorMessage] = useState<string | null>("");

    const formRef = useRef<HTMLDivElement>(null);
    const infoRef = useRef<HTMLDivElement>(null);
    const popupRef = useRef<HTMLDivElement>(null);

    const api_url = import.meta.env.VITE_API_URL;
    const api_url_platform = "https://sprain-reiterate-cape.ngrok-free.dev";

    //get user info
    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const res = await fetch(`${api_url}/auth/profile`, {
                    headers: {"Content-Type": "application/json"},
                    credentials: "include"
                });
                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail || data.detail.msg || "Failed to load profile");
                    return;
                }

                setCurrUsername(data.username);
                setUsername(data.username);

                setCurrEmail(data.email);
                setEmail(data.email);

            } catch (e) {
                console.error("Failed to load profile:", e);
            }
        };

        fetchProfile();
    }, []);

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
                    console.error(data.detail || data.detail.msg || "Failed to load profile");
                    return;
                }
                setProjects(data);

            } catch (e) {
                console.error("Failed to load projects:", e);
            }
        };

        fetchProjects();
    }, []);

    // update profile info
    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();

        const error = validateProfileUpdate();
        if (error) {
            setErrorMessage(error);
            setUsername(currUsername);
            setEmail(currEmail);
            return;
        }
        setErrorMessage("");

        try{
            const res = await fetch(`${api_url}/auth/profile`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({"username": username, "email": email})
            });

            const data = await res.json();

            if (!res.ok) {
                const raw_message = data.detail?.[0]?.msg || data.detail || "Failed to update profile";
                const msg = raw_message.replace("Value error, ", "");
                console.error(raw_message);
                setErrorMessage(msg);
                setUsername(currUsername);
                setEmail(currEmail);
                return;
            }

            setUsername(username);
            setEmail(email);
            setCurrUsername(username);
            setCurrEmail(email);

            setConfirmMessage("Profile updated successfully");
            console.log("Profile updated successfully");

        }catch(e: any){
            console.error("Failed to update profile:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorMessage(msg);
            setUsername(currUsername);
            setEmail(currEmail);
        }
    }
    const validateProfileUpdate = (): string | null => {
        if (!username || !email) {
            return "Some required fields are missing";
        }

        const newUsername = currUsername !== username ? username : undefined;
        const newEmail = currEmail !== email ? email : undefined;

        if (!newUsername && !newEmail) {
            return "No Change Detected";
        }
        return null;
    };

    // handle change password
    const handleNewPassword = async (e: React.FormEvent) => {
        e.preventDefault();

        const error = validatePasswordChange();
        if (error) {
            setErrorMessage(error);
            return;
        }
        setErrorMessage("");

        try {
            const res = await fetch(`${api_url}/auth/profile`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({"current_password": password, "new_password": newPassword})
            });

            const data = await res.json();

            if (!res.ok) {
                const raw_message = data.detail?.[0]?.msg || data.detail || "Failed to change password";
                const msg = raw_message.replace("Value error, ", "");
                console.error(raw_message);
                setErrorMessage(msg);
                return;
            }
            setPassword("");
            setNewPassword("");
            setConfirmPassword("");

            setConfirmMessage("Password changed successfully");
            console.log("Password changed successfully");

        } catch (e: any){
            console.error("Failed to change password:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorMessage(msg);
        }
    };
    const validatePasswordChange = () : string | null => {
        if (newPassword !== confirmPassword){
            return "Confirmed Password does not match new password";
        }

        if (!password || !newPassword || !confirmPassword) {
            return "Some required fields are missing";
        }
        return null;
    };

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
                    "repo_url": repoURL,
                    "target_platform": targetPlatform
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
            console.log("Project added successfully:", newProject);

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

    const handleConnectGithub = () => {
        window.location.href = `${api_url_platform}/platform/github/connect`;
    };

    const handleConnectGitlab = () => {
        window.location.href = `${api_url_platform}/platform/gitlab/connect`;
    };

    const handleInstallApp = () => {
        window.location.href = `${api_url_platform}/github/install_app`;
    };

    // Close info popup on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (projectInfoId && infoRef.current &&
                    !infoRef.current.contains(e.target as Node)) {
                    setProjectInfoId(null);
                }

                if((confirmMessage || errorMessage) && popupRef.current &&
                        !popupRef.current.contains(e.target as Node)){
                    setConfirmMessage("");
                    setErrorMessage("");
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , [projectInfoId, confirmMessage, errorMessage]);

    return(
        <div className={styles.pageContainer}>
            {projectInfoId &&
                <ProjectInfo
                    projectInfoId={projectInfoId}
                    setProjectInfoId={setProjectInfoId}
                    projects={projects}
                    setProjects={setProjects}
                    infoRef={infoRef}
                    popupRef={popupRef}
                    />
            }
            <div className={styles.tabsBar}>
                <p className={styles.tabsHeader}>Account Settings</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[0])}>{tabs[0]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[1])}>{tabs[1]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[2])}>{tabs[2]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[3])}>{tabs[3]}</p>
            </div>
            
            <div className={styles.formContainer} ref={formRef}>
                {(!activeTab || activeTab === tabs[0]) && (
                    <ProfileTab 
                        username={username} 
                        email={email} 
                        setUsername={setUsername} 
                        setEmail={setEmail} 
                        handleUpdateProfile={handleUpdateProfile}
                    />
                )}

                {(!activeTab || activeTab === tabs[1]) && (
                    <SecurityTab 
                        password={password} 
                        newPassword={newPassword}
                        confirmPassword={confirmPassword} 
                        setPassword={setPassword} 
                        setNewPassword={setNewPassword}
                        setConfirmPassword={setConfirmPassword} 
                        showPassword={showPassword} 
                        showNewPassword={showNewPassword}
                        showConfirmPassword={showConfirmPassword}
                        setShowPassword={setShowPassword}
                        setShowNewPassword={setShowNewPassword}
                        setShowConfirmPassword={setShowConfirmPassword}
                        handleSubmitNewPassword={handleNewPassword}
                    />
                )}

                {(!activeTab || activeTab === tabs[2]) && (
                    <ProjectsTab 
                        projects={projects} 
                        projectName={projectName}
                        setProjectName={setProjectName}
                        repoURL={repoURL}
                        setRepoUrl={setRepoUrl}
                        targetPlatform={targetPlatform}
                        setTargetPlatform={setTargetPlatform}
                        handleSubmitProject={handleAddProject}
                        setProjectInfoId={setProjectInfoId}
                    />
                )}

                {(!activeTab || activeTab === tabs[3]) && (
                    <PlatformsTab
                        handleConnectGithub={handleConnectGithub}
                        handleConnectGitlab={handleConnectGitlab}
                        handleInstallApp={handleInstallApp}
                    />
                )}
            </div>

            {(errorMessage || confirmMessage) && 
                <Popup 
                    btnText1={"Got it"}
                    btn1Action={null}
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

export default UserProfile;
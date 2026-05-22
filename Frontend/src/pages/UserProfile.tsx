import gStyles from "../global.module.css"
import styles from './UserProfile.module.css'
import type { Project, Platform } from "../types";
import { ProfileTab, SecurityTab, ProjectsTab } from "../components/UserProfile/Tabs";
import { useState, useEffect } from "react";


const tabs = ["Profile", "Security", "Projects", "Platforms"];

function UserProfile() {
    const [activeTab, setActiveTab] = useState<string>(tabs[0]);
    
    //fields
    const [currUsername, setCurrUsername] = useState("");
    const [username, setUsername] = useState("");
    const [currEmail, setCurrEmail] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [projects, setProjects] = useState<Project[]>([]);

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
                    credentials: "include"
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

    const handleUpdateProfile = async (e: React.FormEvent) => {
        console.log("Updating profile...");
        e.preventDefault();
        const newUsername = currUsername !== username ? username : undefined;
        const newEmail = currEmail !== email ? email : undefined;

        if (!newUsername && !newEmail) {
            console.log("No changes to update");
            return;
        }

        try{
            const res = await fetch(`${api_url}/auth/profile`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({newUsername, newEmail})
            });

            const data = await res.json();

            console.log("Response status:", res.status, "url:", res.url);
            console.log("Response data:", data);

            if (!res.ok) {
                console.error(data.detail || data.detail.msg || "Failed to update profile");
                return;
            }
            console.log("Profile updated successfully");


        }catch(e){
            console.error("Failed to update profile:", e);
        }
    }

    const handleConnectGithub = () => {
        window.location.href = `${api_url_platform}/platform/github/connect`;
    };

    const handleConnectGitlab = () => {
        window.location.href = `${api_url_platform}/platform/gitlab/connect`;
    };

    const handleInstallApp = () => {
        window.location.href = `${api_url_platform}/github/install_app`;
    };

    return(
        <div className={styles.pageContainer}>
            <div className={styles.tabsBar}>
                <p>Search</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[0])}>{tabs[0]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[1])}>{tabs[1]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[2])}>{tabs[2]}</p>
                <div className={styles.devider}/>
                <p className={`${styles.tab} ${gStyles.clickable}`} onClick={() => setActiveTab(tabs[3])}>{tabs[3]}</p>
            </div>
            
            <div className={styles.formContainer}>
                {activeTab === tabs[0] && (
                    <ProfileTab 
                        username={username} 
                        email={email} 
                        setUsername={setUsername} 
                        setEmail={setEmail} 
                        handleUpdateProfile={handleUpdateProfile}
                    />
                )}

                {activeTab === tabs[1] && (
                    <SecurityTab 
                        password={password} 
                        confirmPassword={confirmPassword} 
                        setPassword={setPassword} 
                        setConfirmPassword={setConfirmPassword} 
                        showPassword={showPassword} 
                        setShowPassword={setShowPassword}
                    />
                )}

                {activeTab === tabs[2] && (
                    <ProjectsTab 
                        projects={projects} 
                        setProjects={setProjects} 
                    />
                )}

                {activeTab === tabs[3] && (
                    <div className={styles.section}>
                        <h1 className={styles.header}>{tabs[3]}</h1>
                        <button onClick={handleConnectGithub} className={`${gStyles.clickable}`}>Connect with github account</button>
                        <button onClick={handleConnectGitlab} className={`${gStyles.clickable}`}>Connect with gitlab account</button>
                        <button onClick={handleInstallApp} className={`${gStyles.clickable}`}>Install app</button> 
                    </div>
                )}
            </div>
        </div>
    );
}

export default UserProfile;
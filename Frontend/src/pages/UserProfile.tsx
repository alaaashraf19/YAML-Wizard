import gStyles from "../global.module.css"
import styles from './UserProfile.module.css'
import { Platforms, type Project } from "../types";

import ProfileTab from "../components/UserProfile/ProfileTab";
import PlatformsTab from "../components/UserProfile/PlatformsTab";
import ProjectsTab from "../components/UserProfile/ProjectsTab";
import ProjectInfoTab from "../components/UserProfile/ProjectInfoTab";
import SecurityTab from "../components/UserProfile/SecurityTab";

import Popup from "../components/Popup/Popup"
import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";


const tabs = ["Profile", "Platforms", "Projects", "Security"];

function UserProfile() {
    const [searchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState<string | null>(searchParams.get("tab") || null);
    
    const [projects, setProjects] = useState<Project[]>([]);
    const [projectInfoId, setProjectInfoId] = useState<number | null>(null);

    const [confirmMessage, setConfirmMessage] = useState<string | null>("");
    const [warningMessage, setWarningMessage] = useState<string | null>("");
    const [errorMessage, setErrorMessage] = useState<string | null>("");

    const navigate = useNavigate();
    const startRef = useRef<HTMLDivElement>(null);
    const formRef = useRef<HTMLDivElement>(null);
    const infoRef = useRef<HTMLDivElement>(null);
    const popupRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to top smoothly
    useEffect(() => {
        startRef.current?.scrollIntoView({ behavior: "smooth" });
    }, []);

    // Get current active tab from url
    useEffect(() => {
        setActiveTab(searchParams.get("tab") || null);
    }, [searchParams]);

    // check if project info id is selected
    useEffect(() => {
        const projectId = sessionStorage.getItem("project_id");

        if(projectId){
            setProjectInfoId(Number(projectId));
        }
    }, []);

    // Close info popup on outside click
    // useEffect(
    //     () => {
    //         function handleClickOutside(e: MouseEvent) {
    //             if (projectInfoId && infoRef.current &&
    //                 !infoRef.current.contains(e.target as Node)) {
    //                 setProjectInfoId(null);
    //             }

    //             if((confirmMessage || errorMessage) && popupRef.current &&
    //                     !popupRef.current.contains(e.target as Node)){
    //                 setConfirmMessage("");
    //                 setErrorMessage("");
    //             }
    //         }

    //         document.addEventListener("mousedown", handleClickOutside);
    //         return () => {
    //             document.removeEventListener("mousedown", handleClickOutside);
    //         };
    //     }
    // , [projectInfoId, confirmMessage, errorMessage]);

    return(
        <div className={styles.pageContainer}>
            <div ref={startRef}/>

            <div className={styles.tabsBar}>
                <p className={`${styles.tabsHeader} ${gStyles.clickable}`}
                    onClick={() => navigate("/profile")}>Account Settings</p>

                {tabs.map((tab, index) => (
                    <div key={index}>
                        <div className={styles.devider}/>
                        <p className={`${styles.tab} ${gStyles.clickable}`}
                            onClick={() => navigate(`/profile?tab=${tab}`)}>{tab}</p>
                    </div>
                ))}
            </div>
                        
            {projectInfoId &&
                <ProjectInfoTab
                    projectInfoId={projectInfoId}
                    setProjectInfoId={setProjectInfoId}
                    projects={projects}
                    setProjects={setProjects}
                    infoRef={infoRef}
                    popupRef={popupRef}
                    />
            }

            <div className={styles.formContainer} ref={formRef}>
                {(!activeTab || activeTab === tabs[0]) && (
                    <ProfileTab 
                        setConfirmMessage={setConfirmMessage}
                        setErrorMessage={setErrorMessage}
                    />
                )}

                {(!activeTab || activeTab === tabs[1]) && (
                    <PlatformsTab
                        setConfirmMessage={setConfirmMessage}
                        setWarningMessage={setWarningMessage}
                        setErrorMessage={setErrorMessage}
                    />
                )}

                {(!activeTab || activeTab === tabs[2]) && (
                    <ProjectsTab 
                        activeTab={activeTab}
                        projects={projects}
                        setProjects={setProjects}
                        setProjectInfoId={setProjectInfoId}
                        setConfirmMessage={setConfirmMessage}
                        setErrorMessage={setErrorMessage}
                    />
                )}
                
                {(activeTab === tabs[3]) && (
                    <SecurityTab 
                        setConfirmMessage={setConfirmMessage}
                        setErrorMessage={setErrorMessage}
                    />
                )}
            </div>

            {(errorMessage || confirmMessage) && 
                <Popup 
                    btnText1={"Got it"}
                    btn1Action={
                        Platforms.find(p => searchParams.get(p) !== null)? () => navigate("/profile"): null}
                    btnText2={null}
                    btn2Action={null}
                    confirmMessage={confirmMessage}
                    setConfirmMessage={setConfirmMessage}
                    warningMessage={warningMessage}
                    setWarningMessage={setWarningMessage}
                    errorMessage={errorMessage}
                    setErrorMessage={setErrorMessage}
                    popupRef={popupRef}
                />
            }
        </div>
    );
}

export default UserProfile;
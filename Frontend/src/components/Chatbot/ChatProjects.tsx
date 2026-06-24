import gStyles from "../../global.module.css"
import styles from "./ChatProjects.module.css";
import { useEffect, useState } from "react";
import type { Project } from "../../types";

import { IoClose } from "react-icons/io5";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

type projects_props = {
    sessionId: number | null,
    setProject: React.Dispatch<React.SetStateAction<Project | null>>,
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setIsMenuOpen: React.Dispatch<React.SetStateAction<boolean>>,
    menuRef: React.Ref<HTMLDivElement> | null
}

function ChatProjects({ sessionId, setProject, setConfirmMessage, setErrorMessage, setIsMenuOpen, menuRef}: projects_props) {
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");

    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    const filteredProjects = projects ? projects
        .filter(p => p.project_name.toLowerCase().includes(query.toLowerCase())) : [];


    const handleProjectSelect = async (project: Project) => {
        try {
            const res = await fetch(`${api_url}/chatbot/sessions/${sessionId}/projects/${project.id}`, {
                credentials: "include",
                method: "POST",
                headers: {"Content-Type": "application/json"},
                // body: JSON.stringify({})
            });

            const data = await res.json();

            if (!res.ok) {
                const msg = data.detail?.[0]?.msg || data.detail || "Failed to connect project to this session";
                console.error(msg);
                setErrorMessage(msg);
                return;
            }
            setProject(data);
            setIsMenuOpen(false);
            setConfirmMessage("here");

        } catch (e) {
            console.error("Failed to connect project to this session:", e);
            setErrorMessage("Failed to connect project to this session");
        }
    };

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

    return createPortal(
        <div className={styles.menu} ref={menuRef}>
            <div className={styles.projectsButtons}>
                <button className={`${styles.closeMenuButton} ${gStyles.clickable}`}
                    onClick={() => {setIsMenuOpen(false);}} title={"Close Menu"}>
                    <IoClose />
                </button>
                <button className={`${styles.addButton} ${gStyles.clickable}`}
                    onClick={() => navigate("/profile?tab=Projects")} title="Go to settings">
                    Add project
                </button>
            </div>

            <div className={styles.projectsContainer}>
                <div className={styles.searchContainer}>
                    <input type="text" className={styles.searchBar} name="searchBar" value={query}
                        placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                    <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>
                </div>
                
                {filteredProjects.length > 0? (
                    <ul className={styles.list}>
                        {filteredProjects.map((p, index) => (
                            <li key={index} onMouseDown={() => handleProjectSelect(p)}
                                className={`${styles.project} ${gStyles.clickable}`}
                                title={p.project_name+'('+p.repo_url+')'}>
                                <span className={styles.projectName}>{p.project_name}</span>
                                <span className={styles.subInfo}>{p.platform.toUpperCase()}</span>
                            </li>
                        ))}
                    </ul>
                ): (
                    <p className={styles.menuNoProjects}>No projects found</p>
                )}
            </div>
        </div>
    , document.body)
}

export default ChatProjects;
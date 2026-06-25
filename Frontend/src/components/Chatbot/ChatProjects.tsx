import gStyles from "../../global.module.css"
import styles from "./ChatProjects.module.css";
import { useEffect, useMemo, useRef, useState } from "react";
import { Platforms, type Platform, type Project, type Session  } from "../../types";

import { IoClose } from "react-icons/io5";
import { FiFilter } from "react-icons/fi";

import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

type projects_props = {
    sessionId: number | null,
    setProject: React.Dispatch<React.SetStateAction<Project | null>>,
    setSessions: React.Dispatch<React.SetStateAction<Session[]>>,
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setIsMenuOpen: React.Dispatch<React.SetStateAction<boolean>>,
    menuRef: React.Ref<HTMLDivElement> | null
}

function ChatProjects({ sessionId, setProject, setSessions, setConfirmMessage, setErrorMessage, setIsMenuOpen, menuRef}: projects_props) {
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");
    const [filterPlatfrom, setFilterPlatform] = useState<Platform | null>(null);
    const [openFilterMenu, setOpenFilterMenu] = useState<boolean>(false);

    const filterRef = useRef<HTMLDivElement | null>(null);
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    // filter projects by query and selected platform
    const filteredProjects = useMemo(() => {
        return projects ? projects
            .filter(p => {
                return p.project_name.toLowerCase().includes(query.toLowerCase()) &&
                (!filterPlatfrom || p.platform === filterPlatfrom)
            })
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [projects, filterPlatfrom, query]);


    //link project to a session
    const handleProjectSelect = async (project: Project) => {
        if(!sessionId){
            const selectedProject = projects.find(p => p.id === project.id);
            setProject(selectedProject ?? null);
            setIsMenuOpen(false);
            setConfirmMessage(`Connected to ${selectedProject?.project_name} — project context is enabled for this chat`);
            return;
        }

        try {
            const res = await fetch(`${api_url}/chatbot/sessions/${sessionId}/projects/${project.id}`, {
                credentials: "include",
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });

            const data = await res.json();

            if (!res.ok) {
                const msg = data.detail?.[0]?.msg || data.detail || "Failed to connect project to this session";
                console.error(msg);
                setErrorMessage(msg);
                return;
            }
            setProject(data);
            setSessions(prev => prev.map(s => s.id === sessionId 
                ? { ...s, project: data} : s));
            // setIsMenuOpen(false);
            console.log("reached before popup");
            setConfirmMessage(`Connected to ${data.project_name} — project context is enabled for this chat`);

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

    // Close filter menu on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (filterRef.current &&
                    !filterRef.current.contains(e.target as Node)) {
                    setOpenFilterMenu(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

    return createPortal(
        <div className={styles.menu} ref={menuRef}>
            <div className={styles.projectsButtons}>
                <button className={`${styles.closeMenuButton} ${gStyles.clickable}`}
                    onClick={() => {setIsMenuOpen(false);}} title={"Close Menu"}>
                    <IoClose />
                </button>
                <button className={`${styles.addButton} ${gStyles.clickable}`}
                    onClick={() => navigate("/profile?tab=Projects")} title="Go to settings">
                    Manage Projects
                </button>
            </div>

            <div className={styles.projectsContainer}>
                <div className={styles.searchContainer}>
                    <input type="text" className={styles.searchBar} name="searchBar" value={query}
                        placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                    <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>

                    <div className={styles.filterContainer} ref={filterRef}>
                        <FiFilter className={`${styles.filterIcon} ${gStyles.clickable}`} title="Filter"
                            onClick={() => setOpenFilterMenu(prev => !prev)} />
                        {openFilterMenu &&
                            <div className={styles.filterMenu}>
                                <span className={`${styles.option} ${filterPlatfrom? 
                                    `${styles.notSelected} ${gStyles.clickable}` : styles.selected }`}
                                    onClick={() => {setFilterPlatform(null); setOpenFilterMenu(false);}}>
                                    All Platforms</span>
                                {Platforms.map(p => (
                                    <span className={`${styles.option} ${p === filterPlatfrom? styles.selected 
                                        : `${styles.notSelected} ${gStyles.clickable}`}`}
                                        onClick={() => {setFilterPlatform(p); setOpenFilterMenu(false);}}>
                                        {p.toUpperCase()}</span>))}
                            </div>
                        }
                    </div>
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
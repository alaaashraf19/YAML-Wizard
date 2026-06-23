import gStyles from "../../global.module.css"
import styles from "./ChatProjects.module.css";
import { useEffect, useState } from "react";
import type { Project } from "../../types";

import { IoClose } from "react-icons/io5";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

type projects_props = {
    setIsMenuOpen: React.Dispatch<React.SetStateAction<boolean>>,
    setSelectedProject: React.Dispatch<React.SetStateAction<string | React.ReactNode>>,
    menuRef: React.Ref<HTMLDivElement> | null
}

function ChatProjects({setIsMenuOpen, setSelectedProject, menuRef}: projects_props) {
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    const filteredItems = projects ? projects
        .filter(p => p.project_name.toLowerCase().includes(query.toLowerCase()))
        .map(p => p.project_name) : [];

    const handleProjectSelect = (name: string) => {
        setSelectedProject(name);
        setIsMenuOpen(false);
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
            <div className={styles.searchContainer}>
                <input type="text" className={styles.searchBar} name="searchBar"
                    placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                    
                {filteredItems.length > 0? (
                    <ul className={styles.list}>
                        {filteredItems.map((item, index) => (
                            <li key={index} onMouseDown={() => handleProjectSelect(item)}
                                className={`${styles.menuItem} ${gStyles.clickable}`}>
                                {item}
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
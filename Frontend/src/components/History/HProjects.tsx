import gStyles from "../../global.module.css"
import styles from './HProjects.module.css'
import logo from "../../assets/yaml_wizard_logo.png";
import type { Project } from "../../types";
// import Projects from "../components/Chatbot/Projects";

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { IoClose } from "react-icons/io5";
import { FaPlus } from "react-icons/fa";


function HProjects(){
    const [projectId, setProjectId] = useState<number | null>();
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

    const api_url = import.meta.env.VITE_API_URL;
    const navigate = useNavigate();

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

    const filteredItems = projects ? projects
        .filter(p => p.project_name.toLowerCase().includes(query.toLowerCase())) : [];

    return(
        <div className={`${styles.menu} ${isCollapsed ? styles.collapsed : styles.expanded}`}>
            {isCollapsed? (<>
                <LuPanelRightClose className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    onClick={() => setIsCollapsed(prev => !prev)} title={"Expand"}/>
                <FaPlus className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    onClick={() => navigate("/profile?tab=Projects")} title="Add Project"/>
            </>) : (<>
                <div className={styles.appNameContainer}>
                    <img src={logo} alt="" className={`${styles.logo} ${gStyles.clickable}`}
                        title="Go to home page" onClick={() => navigate("/")}/>
                    <span className={`${styles.appName} ${gStyles.clickable}`}
                        title="Go to home page" onClick={() => navigate("/")}>
                        YAML Wizard</span>
                    <LuPanelLeftClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                        onClick={() => setIsCollapsed(prev => !prev)} title={"Collapse"}/>
                </div>

                <p className={styles.projectsStart}>Your Projects</p>
                <div className={styles.projectsContainer}>
                    <div className={styles.searchContainer}>
                        <input type="text" className={styles.searchBar} name="searchBar" value={query}
                            placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                        <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>
                    </div>

                    {filteredItems.length > 0? (
                        <ul className={styles.projectsList}>
                            {filteredItems.map((p, index) => (
                                <li key={index} onMouseDown={() => setProjectId(p.id)}
                                    title={p.project_name + '('+ p.repo_url + ')'}
                                    className={`${styles.project} ${(p.id == projectId)? styles.active : gStyles.clickable}`}>
                                    {p.project_name}
                                </li>
                            ))}
                        </ul>
                    ): (
                        <p className={styles.menuNoProjects}>No projects found</p>
                    )}
                </div>

                <div className={styles.bottomContainer}>
                    <button className={`${styles.addButton} ${gStyles.clickable}`}
                        onClick={() => navigate("/profile?tab=Projects")} title="Go to settings">
                        Add project
                    </button>
                </div>
            </>)}
        </div>
    );
}

export default HProjects;
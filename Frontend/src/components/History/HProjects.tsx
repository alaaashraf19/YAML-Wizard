import gStyles from "../../global.module.css"
import styles from './HProjects.module.css'
import logo from "../../assets/yaml_wizard_logo.png";
import { Platforms, type Platform, type Project } from "../../types";

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { IoClose } from "react-icons/io5";
import { FaPlus } from "react-icons/fa";
import { FiFilter } from "react-icons/fi";


type HPProps = {
    projectId: number | null,
    setProject: React.Dispatch<React.SetStateAction<Project | null>>
}

function HProjects({ projectId, setProject }: HPProps){
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");
    const [filterPlatfrom, setFilterPlatform] = useState<Platform | null>(null);
    const [openFilterMenu, setOpenFilterMenu] = useState<boolean>(false);
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

    const filterRef = useRef<HTMLDivElement | null>(null);
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

    // filter projects by query and selected platform
    const filteredProjects = useMemo(() => {
        return projects ? projects
            .filter(p => {
                return p.project_name.toLowerCase().includes(query.toLowerCase()) &&
                (!filterPlatfrom || p.platform === filterPlatfrom)
            })
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [projects, filterPlatfrom, query]);

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
                        <ul className={styles.projectsList}>
                            {filteredProjects.map((p, index) => (
                                <li key={index} onMouseDown={() => setProject(p)}
                                    title={p.project_name + '('+ p.repo_url + ')'}
                                    className={`${styles.project} ${(p.id === projectId)? styles.active : gStyles.clickable}`}>
                                    <span className={styles.projectName}>{p.project_name}</span>
                                    <span className={styles.subInfo}>{p.platform.toUpperCase()}</span>
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
                        Manage Projects
                    </button>
                </div>
            </>)}
        </div>
    );
}

export default HProjects;
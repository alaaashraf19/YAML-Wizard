import gStyles from "../../global.module.css"
import styles from './HProjects.module.css'
import logo from "../../assets/yaml_wizard_logo.png";
import { useAuth } from '../../Context/AuthContext';
import type { Project } from "../../types";
// import Projects from "../components/Chatbot/Projects";

import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { IoPerson } from "react-icons/io5";
import { GoPerson } from "react-icons/go";
import { FaPlus, FaSignOutAlt } from "react-icons/fa";


function HProjects(){
    const [projectId, setProjectId] = useState<number | null>();
    const [projects, setProjects] = useState<Project[]>([]);
    const [query, setQuery] = useState("");
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
    const [openSettings, setOpenSettings] = useState<boolean>(false);

    const settingsRef = useRef<HTMLDivElement | null>(null);
    const avatarRef = useRef<HTMLDivElement | null>(null);
    const avatarIconRef = useRef<HTMLDivElement | null>(null);

    const api_url = import.meta.env.VITE_API_URL;
    const { username, loading, logout } = useAuth();
    const navigate = useNavigate();

    
    // Close options on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (settingsRef.current &&
                    !settingsRef.current.contains(e.target as Node) && 
                    ((avatarRef.current && 
                    !avatarRef.current.contains(e.target as Node)) ||
                    (avatarIconRef.current &&
                    !avatarIconRef.current.contains(e.target as Node)))) {
                    setOpenSettings(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

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

                <div ref={avatarIconRef} className={styles.settingsContainer}>
                    <GoPerson className={`${styles.username} ${gStyles.clickable}`} title={"Open Menu"}
                        onClick={() => setOpenSettings(prev => !prev)}/>
                    {openSettings &&
                        <div className={styles.settingsMenu} ref={settingsRef}>
                            <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                                <IoPerson/>
                                Profile
                            </Link>
                            <Link className={`${styles.option} ${gStyles.clickable}`} to="/"
                                onClick={() => logout()}>
                                <FaSignOutAlt/> Sign out
                            </Link>
                        </div>
                    }
                </div>
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
                    <input type="text" className={styles.searchBar} name="searchBar"
                        placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                        
                    {filteredItems.length > 0? (
                        <ul className={styles.projectsList}>
                            {filteredItems.map((p, index) => (
                                <li key={index} onMouseDown={() => setProjectId(p.id)}
                                    className={`${styles.project} ${gStyles.clickable} ${(p.id == projectId) && styles.active}`}>
                                    {p.project_name}
                                </li>
                            ))}
                        </ul>
                    ): (
                        <p className={styles.menuNoProjects}>No projects found</p>
                    )}
                </div>

                <div className={styles.bottomContainer}>
                    <div className={styles.addBtnContainer}>
                        <button className={`${styles.addButton} ${gStyles.clickable}`}
                            onClick={() => navigate("/profile?tab=Projects")} title="Go to settings">
                            Add project
                        </button>
                    </div>

                    {!loading && (
                        <div ref={avatarRef} className={styles.settingsContainer}>
                            <button className={`${styles.username} ${gStyles.clickable}`} title={"Open Menu"}
                                onClick={() => setOpenSettings(prev => !prev)}>
                                <GoPerson/>{username}
                            </button>
                            {openSettings && 
                                <div className={styles.settingsMenu} ref={settingsRef}>
                                    <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                                        <IoPerson/>
                                        Profile
                                    </Link>
                                    <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={() => logout()}>
                                        <FaSignOutAlt/>
                                        Sign out
                                    </Link>
                                </div>
                            }
                        </div>
                    )}
                </div>
            </>)}
        </div>
    );
}

export default HProjects;
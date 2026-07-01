import gStyles from "../../global.module.css"
import styles from './HProjects.module.css'
import logo from "../../assets/yaml_wizard_logo.png";
import { Platforms, type Platform, type Project } from "../../types";
import { useHistoryStore } from "../../pages/History";

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { IoClose } from "react-icons/io5";
import { FaLinesLeaning } from "react-icons/fa6";
import { FiFilter } from "react-icons/fi";

import { create } from "zustand";
import {persist,createJSONStorage} from "zustand/middleware";
import Popup from "../Popup/Popup";


type HPProps = {
    isEdit: boolean,
    setDiscardChanges: React.Dispatch<React.SetStateAction<boolean>>,
}

type HistoryProjectsStore={
    isCollapsed: boolean,
    setIsCollapsed: (isCollapsed: boolean) => void
}

const useHProjectsStore = create<HistoryProjectsStore>()(
    persist((set)=>({
        isCollapsed: false,
        setIsCollapsed: isCollapsed => set({isCollapsed})
    }),{
        name: "history_projects_store",
        storage: createJSONStorage(() => sessionStorage)
    })
)

function HProjects({ isEdit, setDiscardChanges }: HPProps){
    const projectId: number | null = useHistoryStore(s=>s.project?.id ?? null);
    const {setProject, setPipeline, setIsEdit} = useHistoryStore();
    
    const {isCollapsed, setIsCollapsed}=useHProjectsStore();
    
    const [projects, setProjects] = useState<Project[]>([]);
    const [tempProject, setTempProject] = useState<Project | null>(null);
    const [query, setQuery] = useState<string>("");
    const [filterPlatfrom, setFilterPlatform] = useState<Platform | null>(null);
    const [openFilterMenu, setOpenFilterMenu] = useState<boolean>(false);
    
    const [askDiscard, setAskDiscard] = useState<string | null>(null);
    const [warningDiscard, setWarningDiscard] = useState<string | null>(null);

    const filterRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement>(null);
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

    return(
        <div className={`${styles.menu} ${isCollapsed ? styles.collapsed : styles.expanded}`}>
            {isCollapsed? (<>
                <LuPanelRightClose className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    onClick={() => setIsCollapsed(!isCollapsed)} title={"Expand"}/>
                <FaLinesLeaning className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    onClick={() => navigate("/profile?tab=Projects")} title="Manage Projects"/>
            </>) : (<>
                <div className={styles.appNameContainer}>
                    <img src={logo} alt="" className={`${styles.logo} ${gStyles.clickable}`}
                        title="Go to home page" onClick={() => navigate("/")}/>
                    <span className={`${styles.appName} ${gStyles.clickable}`}
                        title="Go to home page" onClick={() => navigate("/")}>
                        YAML Wizard</span>
                    <LuPanelLeftClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                        onClick={() => setIsCollapsed(!isCollapsed)} title={"Collapse"}/>
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
                                <li key={index} title={p.project_name + " ("+ p.repo_url + ')'}
                                    onClick={() => {
                                        isEdit? (
                                            setTempProject(p),
                                            setAskDiscard("Changing the current project will discard all changes!"),
                                            setWarningDiscard("Your unsaved changes cannot be recovered.")
                                        ): (
                                            setProject(p),
                                            setPipeline(null),
                                            setIsCollapsed(true))
                                    }}
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
                    <button className={`${styles.manageButton} ${gStyles.gButton}`}
                        onClick={() => navigate("/profile?tab=Projects")} title="Go to settings">
                        Manage Projects
                    </button>
                </div>
            </>)}

            {askDiscard && 
            <Popup
                btnText1="Discard"
                btn1Action={() => {
                    setProject(tempProject);
                    setTempProject(null);
                    setIsCollapsed(true);
                    setDiscardChanges(true);
                    setIsEdit(false);
                }}
                btnText2="Cancel"
                questionMessage={askDiscard}
                setQuestionMessage={setAskDiscard}
                warningMessage={warningDiscard}
                setWarningMessage={setWarningDiscard}
                popupRef={popupRef}
            />}
        </div>
    );
}

export default HProjects;
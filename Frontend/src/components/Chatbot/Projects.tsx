import gStyles from "../../global.module.css"
import styles from "./Projects.module.css";
import { IoClose } from "react-icons/io5";
import { createPortal } from "react-dom";
import { useState } from "react";

type projects_props = {
    setIsMenuOpen: React.Dispatch<React.SetStateAction<boolean>>,
    setSelectedProject: React.Dispatch<React.SetStateAction<string | React.ReactNode>>,
    menuRef: React.Ref<HTMLDivElement> | null
}

function Projects({setIsMenuOpen, setSelectedProject, menuRef}: projects_props) {

    const [projects] = useState([{ name: "Project 1" }, { name: "Project 2" }, { name: "Project 3" }, { name: "Project 4" }, { name: "Project 5" }, { name: "Project 6" }, { name: "Project 7" }, { name: "Project 8" }, { name: "Project 9" }, { name: "Project 10" }, { name: "Project 11" }, { name: "Project 12" }, { name: "Project 13" }, { name: "Project 14" }, { name: "Project 15" }, { name: "Project 16" }, { name: "Project 17" }, { name: "Project 18" }, { name: "Project 19" }, { name: "Project 20" }]);
    // const [projects] = useState([{ name: "Project Project Project Project Project Project Project Project Project project Project Project Project 1" }, { name: "Project 2" }, { name: "Project 3" }, { name: "Project 4" }, { name: "Project 5" }, { name: "Project 6" }]);
    // const [projects] = useState([]);
    const [query, setQuery] = useState("");

    const filteredItems = projects ? projects
        .filter(p => p.name.toLowerCase().includes(query.toLowerCase()))
        .map(p => p.name) : [];

    const handleProjectSelect = (name: string) => {
        setSelectedProject(name);
        setIsMenuOpen(false);
    };

    return createPortal(
        <div className={styles.menu} ref={menuRef}>
            <div className={styles.projectsButtons}>
                <button className={`${styles.closeMenuButton} ${gStyles.clickable}`}
                    onClick={() => {setIsMenuOpen(false);}} title={"Close Menu"}>
                    <IoClose />
                </button>
                <button className={`${styles.addButton} ${gStyles.clickable}`}>
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

export default Projects;
// import gStyles from "../global.module.css"
import styles from './History.module.css'

import HProjects from "../components/History/HProjects";

// import { useEffect, useRef, useState } from "react";
// import { Link, useNavigate } from "react-router-dom";

// import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
// import { IoPerson } from "react-icons/io5";
// import { GoPerson } from "react-icons/go";
// import { FaSignOutAlt } from "react-icons/fa";


function History(){
    return(
        <div className={styles.window}>
            <HProjects/>
            <div className={styles.yamlWindow}>

            </div>
        </div>
    );
}

export default History;
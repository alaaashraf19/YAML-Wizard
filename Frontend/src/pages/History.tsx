import gStyles from "../global.module.css"
import styles from './History.module.css'

import HProjects from "../components/History/HProjects";

import { FiFilter } from "react-icons/fi";
import { FaPlus, FaMinus } from "react-icons/fa";


function History(){
    return(
        <div className={styles.window}>
            <HProjects/>
            <div className={styles.historyWindow}>
                <p className={styles.header}>Version History</p>
                <div className={styles.namesContainer}>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile1</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                    <p className={`${styles.scriptName} ${gStyles.clickable}`}>Yamlfile2</p>
                </div>
                <FiFilter className={`${styles.filterIcon} ${gStyles.clickable}`} title="Filter"/>
            </div>
            <div className={styles.scriptWindow}>
                <div className={styles.editBar}>
                    <div className={styles.divider}></div>
                    <div className={styles.line}>
                        <FaMinus className={`${styles.lineBtn} ${gStyles.clickable}`} title="Down"/>
                        <FaPlus className={`${styles.lineBtn} ${gStyles.clickable}`} title="Up"/>
                    </div>
                </div>
                <div className={styles.script}></div>
            </div>
        </div>
    );
}

export default History;
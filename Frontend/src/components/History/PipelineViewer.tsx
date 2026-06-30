import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'
import ChatbotBubble from './ChatbotBubble';
import type { Job } from '../../types';
import { useHistoryStore } from "../../pages/History";
import { useState } from 'react';

import { MdEdit } from "react-icons/md";
import { MdBrightness6 } from "react-icons/md";
import { MdBrightness2 } from "react-icons/md";


type ViewerProps = {
    jobs: Job[]
}

function PipelineViewer({ jobs }:ViewerProps){
    const {isDark, setIsDark, setIsEdit, pipeline} = useHistoryStore();
    const [isChatOpen, setIsChatOpen] = useState(false);
        
    let lineNumber = 1;
    return(
        <div className={`${styles.pipeline} ${isDark? styles.dark : styles.bright}`}>
            {!pipeline?.is_active && 
            <div className={styles.btnsContainer}>
                <MdEdit className={`${styles.editBtn} ${gStyles.clickable}`} 
                    title="Open Editor" onClick={() => {setIsEdit(true); console.log(pipeline)}}/>
            </div>
            }

            {jobs.map((job, jobIndex) => {
                let lines = job.content.split("\n");
                let startLine = lineNumber;
                lineNumber += lines.length;
                return(
                    <div key={jobIndex} className={styles.job}>
                        {lines.map((line, index) => {
                            const currentLine=startLine++;
                            return(
                            <div key={index} className={styles.yamlLine}>
                                <span className={styles.lineNumber}>
                                    {currentLine}
                                </span>
                                <span className={styles.lineText}>{line}</span>
                            </div>
                        );})}
                    </div>
                );
            })}

            <div className={`${styles.themeBtn} ${isDark ? styles.dark : ""}`}
                onClick={()=>setIsDark(!isDark)} title="Change Theme">
                <MdBrightness6 className={styles.sunIcon}/>
                <MdBrightness2 className={styles.moonIcon}/>
            </div>
            <ChatbotBubble
                isChatOpen={isChatOpen}
                setIsChatOpen={setIsChatOpen}
            />
        </div>
    );
}

export default PipelineViewer;
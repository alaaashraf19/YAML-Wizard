import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'
import ChatbotBubble from './ChatbotBubble';
import type { Job, Pipeline, Project } from '../../types';
import { useState } from 'react';

import { MdEdit } from "react-icons/md";
import { MdBrightness6 } from "react-icons/md";
import { MdBrightness2 } from "react-icons/md";


type ViewerProps = {
    project: Project,
    pipeline: Pipeline,
    setIsEdit: React.Dispatch<React.SetStateAction<boolean>>,
    isDark: boolean,
    setIsDark: React.Dispatch<React.SetStateAction<boolean>>,
}

function PipelineViewer({ project, pipeline, setIsEdit, isDark, setIsDark }: ViewerProps){
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [jobs] = useState<Job[]>([
    {
        id: "build",
        content: "build:\n  stage: build\n  script:\n    - npm install\n    - npm run build"
    },
    {
        id: "test",
        content: "test:\n  stage: test\n  script:\n    - npm test"
    },
    {
        id: "deploy",
        content: "deploy:\n  stage: deploy\n  script:\n    - npm run deploy"
    }
    ]);
    // const [jobs, setJobs] = useState<Job[]>([]);

    let lineNumber = 1;
    return(
        <div className={`${styles.pipeline} ${isDark? styles.dark : styles.bright}`}>
            <div className={styles.btnsContainer}>
                <MdEdit className={`${styles.editBtn} ${gStyles.clickable}`} 
                    title="Open Editor" onClick={() => setIsEdit(true)}/>
            </div>

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
                onClick={()=>setIsDark(prev=>!prev)} title="Change Theme">
                <MdBrightness6 className={styles.sunIcon}/>
                <MdBrightness2 className={styles.moonIcon}/>
            </div>
            <ChatbotBubble
                project={project}
                pipeline={pipeline}
                isChatOpen={isChatOpen}
                setIsChatOpen={setIsChatOpen}
            />
        </div>
    );
}

export default PipelineViewer;
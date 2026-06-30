import gStyles from "../../global.module.css"
import styles from './Pipeline.module.css'

import type { Job } from "../../types";
import { useSortable } from "@dnd-kit/sortable";
import { useState } from "react";

import { FaGripVertical } from "react-icons/fa";
import { IoIosArrowUp, IoIosArrowDown } from "react-icons/io";
import { BsArrowsCollapse, BsArrowsExpand } from "react-icons/bs";
import { TiDocumentDelete } from "react-icons/ti";


type JobProps={
    job: Job,
    jobIndex: number,
    moveJob: (index:number, direction:-1|1)=>void,
    updateJobContent: (jobIndex: number, content: string) => void,
    deleteJob: (job:number)=>void,
    handleKeyDown: (e:React.KeyboardEvent<HTMLTextAreaElement>,jobIndex:number)=>void
}

function SortableJob({ job, jobIndex, moveJob, updateJobContent, deleteJob, handleKeyDown }: JobProps){
    const{ attributes, listeners, setNodeRef, transform, transition }=useSortable({id:job.id});
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

    const style={ transform:transform
                ? `translate3d(${transform.x}px,${transform.y}px,0)`
                : undefined,
            transition };

    return(
        <div id={job.id}  style={style} key={job.id} className={styles.jobContainer}>
            <div className={styles.editBar}>
                {isCollapsed? 
                    <BsArrowsExpand title="Expand" className={`${styles.collapseBtn} ${gStyles.clickable}`}
                    onClick={() => setIsCollapsed(false)}/>
                : <><BsArrowsCollapse title="Collapse" className={`${styles.collapseBtn} ${gStyles.clickable}`}
                    onClick={() => setIsCollapsed(true)}/>
                    <IoIosArrowUp title="Move Up" className={`${styles.orderBtn} ${gStyles.clickable}`}
                        onClick={() => moveJob(jobIndex, -1)}/>
                    <IoIosArrowDown title="Move Down" className={`${styles.orderBtn} ${gStyles.clickable}`}
                        onClick={() => moveJob(jobIndex, 1)}/>
                    <TiDocumentDelete title="Delete Job" className={`${styles.deleteBtn} ${gStyles.clickable}`}
                        onClick={() => deleteJob(jobIndex)}/>
                </>}
            </div>

            <div className={styles.job} ref={setNodeRef}>
                <FaGripVertical {...attributes} {...listeners} title="Move Job"
                    className={`${styles.dragBtn} ${gStyles.clickable}`}/>

                {isCollapsed ?(
                    <span className={styles.yamlInput }>
                        {job.id}
                    </span>
                ) : (
                <div className={styles.jobContent}>
                    <div className={styles.lineNumber}>
                        {job.content.split("\n").map((_, index) => (
                            <span key={index}>
                                {index + 1}
                            </span>
                        ))}
                    </div>

                    <textarea
                        data-job-index={jobIndex}
                        value={job.content}
                        className={styles.yamlInput}
                        onChange={e => updateJobContent(jobIndex, e.target.value)}
                        onKeyDown={e => handleKeyDown(e, jobIndex)}
                        spellCheck={false}
                    />
                </div>)}
            </div>
        </div>
    );
}

export default SortableJob;
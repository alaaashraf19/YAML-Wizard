import gStyles from "../../global.module.css"
import styles from './VersionsBar.module.css'
import type { Pipeline } from "../../types";
import { useHistoryStore } from "../../pages/History";
import { useEditorStore } from "./PipelineEditor";

import { useEffect, useMemo, useState } from "react";
import { TiArrowRightThick } from "react-icons/ti";
import { IoClose, IoReturnDownForward } from "react-icons/io5";
import { TbArrowBarRight } from "react-icons/tb";
import { HiOutlineDownload } from "react-icons/hi";
import { MdDeleteOutline } from "react-icons/md";
import Popup from "../Popup/Popup";


type VersionsBarProps = {
    mainPipeline: Pipeline | null,
    setMainPipeline: React.Dispatch<React.SetStateAction<Pipeline | null>>,
    setOpenVersionsMenu: React.Dispatch<React.SetStateAction<boolean>>,
    setDiscardChanges: React.Dispatch<React.SetStateAction<boolean>>,
    downloadYaml: (pipeline: Pipeline) => void
}

function VersionsBar({
    mainPipeline, 
    setMainPipeline, 
    setOpenVersionsMenu,
    setDiscardChanges,
    downloadYaml

}: VersionsBarProps) {
    const { setPipeline, isEdit, setIsEdit } = useHistoryStore();
    const { hasChanges } = useEditorStore();

    const [versions, setVersions] = useState<Pipeline[]>(mainPipeline ? [mainPipeline] : []);
    const [query, setQuery] = useState<string>("");
    const [hoverVersion, setHoverVersion] = useState<Pipeline | null>(null);
    const [isHover, setIsHover] = useState<boolean>(false);

    const [selectedAtEdit, setSelectAtEdit] = useState<boolean>(false);
    const [selectedVersion, setSelectedVersion] = useState<Pipeline | null>(null);
    const [deletedVersion, setDeletedVersion] = useState<Pipeline | null>(null);
    const [switchedVersion, setSwitchedVersion] = useState<Pipeline | null>(null);
    const [questionMessage, setQuestionMessage] = useState<string | null>(null);
    const [warningMessage, setWarningMessage] = useState<string | null>(null);

    const api_url = import.meta.env.VITE_API_URL;


    const filteredVersions = useMemo(() => {
        return versions ? versions
            .filter(p => (
                p.name.toLowerCase().includes(query.toLowerCase())
            ))
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [versions, query]);


    //fetch edit versions
    // useEffect(() => {
    //     const fetchVersions = async () => {
    //         try{
    //             // change endpoint 
    //             const res = await fetch(`${api_url}/publish/yaml/${project?.platform}`, {
    //                 method: "POST",
    //                 credentials: "include"
    //             });
    
    //             const data = await res.json();
    
    //             if (!res.ok) {
    //                 console.error(data.detail?.[0]?.msg || data.detail || 
    //                     `Failed to fetch edit version of pipeline ${mainPipeline?.name}`);
    //                 return;
    //             }

    //             setVersions(data);
    //             setMainPipeline(null);
    //         } catch (e) {
    //             console.error("Failed to fetch edit versions:", e);
    //         }

    //     }

    //     if(mainPipeline) fetchVersions();
    // }, [mainPipeline]);

    return (
        <div className={styles.versionBar}>
            <div className={styles.topContainer}>
                <p className={styles.header}>Edit Versions of "{mainPipeline?.name}"</p>
                <TiArrowRightThick className={`${styles.closeIcon} ${gStyles.clickable}`} 
                    onClick={() => setOpenVersionsMenu(false)} title="Close"/>
            </div>

            <div className={styles.searchContainer}>
                <input type="text" className={styles.searchBar} name="searchBar" value={query}
                    placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>
            </div>

            {filteredVersions.length > 0 ? <>
                {filteredVersions.map((p, index) => (
                    <div key={index} className={`${styles.pipelineTab} 
                        ${(p.id === mainPipeline?.id)? styles.active : gStyles.clickable}`}
                        onPointerOver={()=>{setHoverVersion(p);setIsHover(true);}}
                        onPointerLeave={()=>{setHoverVersion(null);setIsHover(false);}}>

                        <p className={`${styles.pipelineName} ${mainPipeline?.id !== p.id && gStyles.clickable}`}
                            onClick={() => {
                                mainPipeline?.id !== p.id && (
                                    isEdit? (
                                        hasChanges? (
                                            setSelectAtEdit(true),
                                            setSelectedVersion(p),
                                            setQuestionMessage("Changing the current version will discard all changes"),
                                            setWarningMessage("Your unsaved changes cannot be recovered.")
                                        ) : (setPipeline(p), setIsEdit(false))
                                    ) : setPipeline(p)
                                )
                            }}>{p.name}</p>

                        {isHover && hoverVersion && 
                            <div className={styles.pipelineBtns}>
                                <MdDeleteOutline title="Delete From History"
                                    className={`${styles.icon} ${gStyles.clickable}`}
                                    onClick={() => {
                                            setDeletedVersion(p),
                                            setQuestionMessage(`Do you want to delete ${p.name}-version?`),
                                            setWarningMessage("This action cannot be recovered, maybe download it before lost.")
                                    }}/>

                                <TbArrowBarRight title="Switch this version with the original"
                                    className={`${styles.icon} ${gStyles.clickable}`}
                                    onClick={() => {
                                        setSwitchedVersion(p);
                                        setQuestionMessage(`Switch version-${p.name} with ${mainPipeline?.name}?`);
                                        setWarningMessage(`Main pipeline -${mainPipeline?.name}- will be inserted in history instead.`);
                                    }}/>

                                <HiOutlineDownload onClick={()=>downloadYaml(p)} title="Download File"
                                    className={`${styles.icon} ${gStyles.clickable}`}/>
                            </div>
                        }
                    </div>
                ))}
            </> : <p className={styles.noPipelines}>No pipelines found.</p>}

            {(selectedAtEdit || deletedVersion || switchedVersion) &&
            <Popup
                btnText1={
                    selectedAtEdit ? "Discard"
                    : deletedVersion? "Delete"
                    :"Switch"
                }
                btn1Action={
                    deletedVersion ? () => {
                        // Handle delete action
                    } : switchedVersion ? () => {
                        // Handle switch action
                    } : () => {
                        setDiscardChanges(true);
                        setPipeline(selectedVersion);
                        setSelectedVersion(null);
                    }
                }
                questionMessage={questionMessage}
                setQuestionMessage={setQuestionMessage}
                warningMessage={warningMessage}
                setWarningMessage={setWarningMessage}
            />}
        </div>
    );
}

export default VersionsBar;
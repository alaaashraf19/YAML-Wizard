import gStyles from "../../global.module.css"
import styles from './HistoryBar.module.css'
import type { Pipeline } from "../../types";
import { useHistoryStore } from "../../pages/History";
import { useEditorStore } from "../History/PipelineEditor";
import { useEffect, useMemo, useRef, useState } from "react";

import { FiFilter } from "react-icons/fi";
import { FaHistory } from "react-icons/fa";
import { IoClose } from "react-icons/io5";

import { HiOutlineDownload, HiOutlineUpload } from "react-icons/hi";
import { MdDeleteOutline } from "react-icons/md";
import { CgSync } from "react-icons/cg";
import Popup from "../Popup/Popup";
import VersionsBar from "./VersionsBar";


type HBProps = {
    pipelines: Pipeline[],
    setPipelines: React.Dispatch<React.SetStateAction<Pipeline[]>>,
    syncPipelines: () => Promise<boolean>,
    setDiscardChanges: React.Dispatch<React.SetStateAction<boolean>>,
}

function HistoryBar({ pipelines, setPipelines, syncPipelines, setDiscardChanges }: HBProps){
    const {pipeline, project, setPipeline, isEdit, setIsEdit, loadingSync} = useHistoryStore();
    const { hasChanges } = useEditorStore();

    const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
    const [deletedPipeline, setDeletedPipeline] = useState<Pipeline | null>(null);
    const [publishedPipeline, setPublishedPipeline] = useState<Pipeline | null>(null);
    const [mainPipeline, setMainPipeline] = useState<Pipeline | null>(null);

    const [hoverPipeline, setHoverPipeline] = useState<Pipeline | null>(null);

    const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
    const [questionMessage, setQuestionMessage] = useState<string | null>(null);
    const [warningDiscard, setWarningMessage] = useState<string | null>(null);
    const [errorPublish, setErrorPublish] = useState<string | null>(null);

    const [syncAtEdit, setSyncAtEdit] = useState<boolean>(false);
    const [deleteAtEdit, setDeleteAtEdit] = useState<boolean>(false);
    const [selectAtEdit, setSelectAtEdit] = useState<boolean>(false);
    
    
    const [query, setQuery] = useState<string>("");
    const [openFilterMenu, setOpenFilterMenu] = useState<boolean>(false);
    const [openVersionsMenu, setOpenVersionsMenu] = useState<boolean>(false);
    const [filterGenerated, setFilterGenerated] = useState<boolean | null>(null);
    const [filterActive, setFilterActive] = useState<boolean | null>(null);
    const [filterAuthor, setFilterAuthor] = useState<string[]>([]);
    // const [filterBranch, setFilterBranch] = useState<string[]>([]);

    const filterRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;

    const authors = useMemo(()=>{
        return[...new Set(pipelines.map(p => p.commit_author))].sort();
    }, [pipelines]);
    // const branches  = useMemo(()=>{
    //     return[...new Set(pipelines.map(p => p.branch))].sort();
    // }, [pipelines]);

    const filteredPipelines = useMemo(() => {
        return pipelines ? pipelines
            .filter(p => (
                p.name.toLowerCase().includes(query.toLowerCase()) &&
                (filterGenerated === null || p.is_generated_by_wizard === filterGenerated) &&
                (filterActive === null || p.is_active === filterActive) &&
                // (filterBranch.length === 0 || filterBranch.includes(p.branch)) &&
                (filterAuthor.length === 0 || filterAuthor.includes(p.commit_author))
            ))
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [pipelines, query, filterGenerated, filterActive, filterAuthor]);


    const deletePipeline = async () => {
        if(!deletedPipeline)return;
        try{
            const res = await fetch(`${api_url}/pipelines/${deletedPipeline.id}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to delete pipeline");
                return;
            }

            // if deleted pipeline is the active one
            if(deletedPipeline === pipeline){
                isEdit? (
                    setQuestionMessage("Deleting the current pipeline will discard all changes"),
                    setWarningMessage("Your unsaved changes cannot be recovered.")
                ) : (setPipeline(null), 
                    setPipelines(prev => prev.filter(pipeline => pipeline.id !== deletedPipeline.id)),
                    setConfirmMessage(`Pipeline is deleted from ${project?.project_name}-project version history`))
            }
            else{
                setPipelines(prev => prev.filter(pipeline => pipeline.id !== deletedPipeline.id));
            }

        } catch (e) {
            console.error("Failed to delete pipeline:", e);
        }
    };

    const publishPipeline = async ()=> {
        if(!publishedPipeline)return;
        try{
            const res = await fetch(`${api_url}/publish/yaml/${project?.platform}`, {
                method: "POST",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.detail?.[0]?.msg || data.detail || "Failed to publish pipeline";
                console.error(errorMsg);
                setErrorPublish(errorMsg);
                return;
            }

            setPipelines(prev => prev.map(p=>p.id === publishedPipeline.id
                ? {...p, is_active: true, commited_at: new Date()} : p));
            setPublishedPipeline(null);
            setConfirmMessage(`Pipeline ${publishedPipeline.name} has been successfully published to ${project?.project_name} repository`);
            setWarningMessage(`URL: ${project?.repo_url}`);

        } catch (e) {
            console.error("Failed to delete publish:", e);
        }
    };

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

    //download file by content
    const downloadYaml=(pipeline: Pipeline)=>{
        const yaml=pipeline?.content;
        const blob=new Blob([yaml],{type:"text/yaml"});
        const url=URL.createObjectURL(blob);
        const a=document.createElement("a");
        a.href=url;
        const name: string = pipeline.name;
        const fullName = name + ((name.slice(-4) === ".yml" || name.slice(-5) === ".yaml") ? "" : ".yml");
        a.download=fullName;
        a.click();
        URL.revokeObjectURL(url);
    };

    return(
        <div className={styles.historyBar}>
            <div className={styles.topContainer}>
                <p className={styles.header}>Pipelines</p>
                {project && 
                    <button className={`${styles.syncBtn} ${loadingSync? styles.spinner : gStyles.clickable}`} 
                        title="Sync" disabled={loadingSync}
                        onClick={async() => {
                            {isEdit ? (
                                setSyncAtEdit(true),
                                setQuestionMessage(
                                "The synchronization found updates to your pipelines.\nContinuing will discard your unsaved changes.\n Do you want to continue?"
                                ),setWarningMessage("Your unsaved changes cannot be recovered.")
                            ): await syncPipelines()
                            }
                        }}><CgSync className={styles.syncIcon}/>
                    </button>
                }
            </div>
            <div className={styles.searchContainer}>
                <input type="text" className={styles.searchBar} name="searchBar" value={query}
                    placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>

                <div className={styles.filterContainer} ref={filterRef}>
                    <FiFilter className={`${styles.icon} ${gStyles.clickable}`} title="Filter"
                        onClick={() => setOpenFilterMenu(prev => !prev)} />

                    {openFilterMenu && (
                    <div className={styles.filterMenu}>
                        <span className={styles.filterHeader}>Source</span>
                        <div className={styles.options}>
                            <span title="Generated By YAMLWizard" className={`${styles.option} ${gStyles.clickable}
                                ${filterGenerated === true? styles.selected : `${styles.notSelected}`}`} 
                                onClick={() => {
                                    filterGenerated? setFilterGenerated(null) : setFilterGenerated(true)
                                }}>
                                YAMLWizard</span>
                            <span className={`${styles.option} ${gStyles.clickable} 
                                ${filterGenerated === false? styles.selected : `${styles.notSelected}`}`}
                                title="Fetched From Repo"
                                onClick={() => {
                                    (filterGenerated === false)? setFilterGenerated(null) : setFilterGenerated(false)
                                }}>
                                Repo</span>
                        </div>

                        <div className={styles.divider} />

                        <span className={styles.filterHeader}>Status</span> 
                        <div className={styles.options}>
                            <span className={`${styles.option} ${gStyles.clickable}
                                ${filterActive? styles.selected : `${styles.notSelected}`}`}
                                onClick={() => {
                                    filterActive ? setFilterActive(null) : setFilterActive(true)
                                }}>
                                Published</span>
                            <span className={`${styles.option} ${gStyles.clickable}
                                ${filterActive === false? styles.selected : `${styles.notSelected}`}`}
                                onClick={() => {
                                    (filterActive === false) ? setFilterActive(null) : setFilterActive(false)
                                }}>
                                Not-Published</span>
                        </div>

                        <div className={styles.divider} />

                        {/* <div className={styles.filterHeader}>
                            <span>Branch</span>
                            <IoClose onClick={() => setFilterBranch([])} title="Remove All"
                                className={`${styles.removeFilter} ${gStyles.clickable}`}/>
                        </div>
                        <div className={styles.options}>
                            {branches.map(branch => (
                                <span key={branch} className={`${styles.option} ${gStyles.clickable}
                                    ${filterBranch.find(b => branch === b) ? styles.selected: `${styles.notSelected}`}`}
                                    onClick={() => {
                                        const foundBranch = filterBranch.includes(branch);
                                        foundBranch ? setFilterBranch(filterBranch.filter(b=>b != branch))
                                        : setFilterBranch([...filterBranch, branch])
                                    }}>
                                    {branch}</span>
                            ))}
                        </div> */}

                        <div className={styles.divider} />

                        <div className={styles.filterHeader}>
                            <span>Author</span> 
                            <IoClose onClick={() => setFilterAuthor([])} title="Remove All"
                                className={`${styles.removeFilter} ${gStyles.clickable}`}/>
                        </div>
                        <div className={styles.options}>
                            {authors.map(author => (
                                <span key={author} className={`${styles.option} ${gStyles.clickable}
                                    ${filterAuthor.find(a => author === a) ? styles.selected : `${styles.notSelected}`}`}
                                    onClick={() => {
                                        const foundAuthor = filterAuthor.includes(author);
                                        foundAuthor? setFilterAuthor(filterAuthor.filter(a=>a != author))
                                        : setFilterAuthor([...filterAuthor, author])
                                    }}
                                >{author}</span>
                            ))}
                        </div>
                    </div>
                )}
                </div>
            </div>
            {filteredPipelines.length > 0 ? <>
            <div className={styles.namesContainer}>
                {filteredPipelines.map((p, index) => {
                    return(<>
                    <div key={index} className={`${styles.pipelineTab} 
                        ${(p.id === pipeline?.id)? styles.active : gStyles.clickable}`}
                        onPointerOver={(e)=>{
                            if (e.target === e.currentTarget) setHoverPipeline(p);
                        }}
                        onPointerLeave={(e)=>{
                            if (e.target === e.currentTarget) setHoverPipeline(null);
                        }}>

                        <p className={`${styles.pipelineName} ${pipeline?.id !== p.id && gStyles.clickable}`}
                            onClick={() => {
                                pipeline?.id !== p.id && (
                                    isEdit? (
                                        hasChanges? (
                                            setSelectedPipeline(p),
                                            setSelectAtEdit(true),
                                            setQuestionMessage("Changing the current pipeline will discard all changes"),
                                            setWarningMessage("Your unsaved changes cannot be recovered.")
                                        ) : (setPipeline(p), setIsEdit(false))
                                    ) : setPipeline(p)
                                )
                            }}>{p.name}</p>

                        {hoverPipeline && <div className={styles.pipelineBtns}>
                            {!(hoverPipeline?.is_active) && <>
                                <MdDeleteOutline title="Delete From History"
                                    className={`${styles.icon} ${gStyles.clickable}`}
                                    onClick={() => {
                                        setDeletedPipeline(p),
                                        isEdit && hasChanges?(
                                            setDeleteAtEdit(true),
                                            setQuestionMessage(`Do you want to discard changes and delete ${p.name}-pipeline?`),
                                            setWarningMessage("Your unsaved changes cannot be recovered.")
                                        ) : (
                                            setQuestionMessage(`Do you want to delete ${p.name}-pipeline?`),
                                            setWarningMessage("This action cannot be recovered, maybe download it before lost.")
                                        )
                                    }}/>
                                <HiOutlineUpload title="Publish"
                                    className={`${styles.icon} ${gStyles.clickable}`}
                                    onClick={() => {
                                        setPublishedPipeline(p);
                                        setQuestionMessage(`Publish pipeline-${p.name} to ${project?.project_name} repository?`);
                                        setWarningMessage(`URL: ${project?.repo_url}`);
                                    }}/>
                            </>}

                            <HiOutlineDownload onClick={()=>downloadYaml(p)} title="Download File"
                                className={`${styles.icon} ${gStyles.clickable}`}/>

                            <FaHistory className={`${styles.versionsIcon} ${gStyles.clickable}`} title="Open Edited Versions"
                                onClick={() => {setMainPipeline(hoverPipeline); setOpenVersionsMenu(true);}} />
                        </div>}

                        </div>
                        {openVersionsMenu && 
                            <VersionsBar
                                mainPipeline={mainPipeline}
                                setPipelines={setPipelines}
                                setMainPipeline={setMainPipeline}
                                setOpenVersionsMenu={setOpenVersionsMenu}
                                setDiscardChanges={setDiscardChanges}
                                downloadYaml={downloadYaml}
                            />}
                    </>);
                })}
            </div> 
            </> : <p className={styles.noPipelines}>No pipelines found.</p>}

            {questionMessage && 
            <Popup
                btnText1={
                    publishedPipeline ? "Publish" : 
                    (deletedPipeline && !isEdit ? "Delete" : "Discard")
                }
                btn1Action={() => {
                    if(syncAtEdit || selectAtEdit || deleteAtEdit){
                        setDiscardChanges(true);
                    }
                    if(syncAtEdit){
                        syncPipelines();
                        setSyncAtEdit(false);
                    }
                    if(selectAtEdit){
                        setPipeline(selectedPipeline);
                        setSelectedPipeline(null);
                        setSelectAtEdit(false);
                    }
                    if(deleteAtEdit || deletedPipeline){
                        deletePipeline();
                        setDeleteAtEdit(false);
                    }
                    if(publishedPipeline){
                        publishPipeline();
                    }
                }}
                btnText2="Cancel"
                questionMessage={questionMessage}
                setQuestionMessage={setQuestionMessage}
                warningMessage={warningDiscard}
                setWarningMessage={setWarningMessage}
            />}
            {(confirmMessage || errorPublish) && <Popup
                btnText1="Got it"
                confirmMessage={confirmMessage}
                setConfirmMessage={setConfirmMessage}
                errorMessage={errorPublish}
                setErrorMessage={setErrorPublish}
                popupRef={popupRef}
            />}
        </div>
    );
}

export default HistoryBar;
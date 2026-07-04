import gStyles from "../../global.module.css"
import styles from './VersionsBar.module.css'
import type { Job, Pipeline } from "../../types";
import { useHistoryStore } from "../../pages/History";
import { useEditorStore } from "./PipelineEditor";

import { useEffect, useMemo, useRef, useState } from "react";
import { FaArrowRightLong } from "react-icons/fa6";
import { IoClose } from "react-icons/io5";
import { TbArrowBarRight } from "react-icons/tb";
import { HiOutlineDownload, HiOutlineUpload } from "react-icons/hi";
import { MdDeleteOutline } from "react-icons/md";
import Popup from "../Popup/Popup";


type VersionsBarProps = {
    mainPipeline: Pipeline | null,
    setJobs: React.Dispatch<React.SetStateAction<Job[]>>,
    setPipelines: React.Dispatch<React.SetStateAction<Pipeline[]>>,
    setMainPipeline: React.Dispatch<React.SetStateAction<Pipeline | null>>,
    setOpenVersionsMenu: React.Dispatch<React.SetStateAction<boolean>>,
    setDiscardChanges: React.Dispatch<React.SetStateAction<boolean>>,
    downloadYaml: (pipeline: Pipeline) => void
}

function VersionsBar({
    mainPipeline,
    setJobs,
    setPipelines,
    setMainPipeline, 
    setOpenVersionsMenu,
    setDiscardChanges,
    downloadYaml

}: VersionsBarProps) {
    const { version, setVersion, project, setPipeline, isEdit, setIsEdit } = useHistoryStore();
    const { hasChanges } = useEditorStore();

    const [versions, setVersions] = useState<Pipeline[]>([]);

    const [query, setQuery] = useState<string>("");
    const [selectedAtEdit, setSelectAtEdit] = useState<boolean>(false);
    const [selectedVersion, setSelectedVersion] = useState<Pipeline | null>(null);
    const [deletedVersion, setDeletedVersion] = useState<Pipeline | null>(null);
    const [approvedVersion, setApprovedVersion] = useState<Pipeline | null>(null);
    const [publishedVersion, setPublishedVersion] = useState<Pipeline | null>(null);

    const [questionMessage, setQuestionMessage] = useState<string | null>(null);
    const [warningMessage, setWarningMessage] = useState<string | null>(null);
    const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const popupRef = useRef<HTMLDivElement>(null);
    const api_url = import.meta.env.VITE_API_URL;


    const filteredVersions = useMemo(() => {
        return versions ? versions
            .filter(p => (
                p.name.toLowerCase().includes(query.toLowerCase())
            ))
            .sort((a,b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()) : [];
    }, [versions, query]);

    //fetch edit versions
    useEffect(() => {
        const fetchVersions = async () => {
            if(!project || !mainPipeline) return;
            try{
                // change endpoint 
                const res = await fetch(`${api_url}/projects/${project.id}/pipelines/${mainPipeline.id}/versions`, {
                    method: "GET",
                    credentials: "include"
                });
    
                const data = await res.json();
    
                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || 
                        `Failed to fetch edit version of pipeline ${mainPipeline?.name}`);
                    return;
                }

                setVersions(data.versions);
            } catch (e) {
                console.error("Failed to fetch edit versions:", e);
            }

        }

        if(mainPipeline) fetchVersions();
    }, [mainPipeline]);

    //get version jobs on change of version
    useEffect(()=> {
        if(!project || !mainPipeline || !version)return;
        const getVersionJobs = async () => {
            try {
                const res = await fetch(`${api_url}/projects/${project?.id}
                    /pipelines/${mainPipeline?.id}/versions/${version.id}/jobs`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });
    
                const data = await res.json();
    
                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to fetch version script");
                    return;
                }

                setJobs(data.jobs);
            }catch(e: any){
                console.error(`Failed to get jobs of version with id: ${version?.id}`)
            }
        }

        if(version){
            setPipeline(null);
            getVersionJobs();
        }

    },[version?.id, mainPipeline?.id, project?.id]);

    const handleSwitchingVersion = (oldVersion: Pipeline, newVersion: Pipeline) => {
        if(!mainPipeline || !project || ! version) return;

        setPipelines(prev => [...prev.filter(pipeline => pipeline.id !== oldVersion.id), newVersion]);
        setVersions(prev => [...prev.filter(version => version.id !== newVersion.id), oldVersion]);
        
        setPipeline(newVersion);
        setVersion(oldVersion);
    };

    const approveVersion = async ()=> {
        if(!project || !mainPipeline || !approvedVersion)return;
        try{
            const res = await fetch(`${api_url}/projects/${project.id}/pipelines/
                ${mainPipeline.id}/versions/${approvedVersion.id}/approve`, {
                method: "POST",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.detail?.[0]?.msg || data.detail || "Failed to publish pipeline";
                console.error(errorMsg);
                setErrorMessage(errorMsg);
                setApprovedVersion(null);
                return;
            }
            handleSwitchingVersion(mainPipeline, approvedVersion);

            setConfirmMessage(`Version ${approvedVersion.name} has been successfully approved`);
            setWarningMessage(`Previous pipeline ${mainPipeline?.name} can be found in version history.\nURL: ${project?.repo_url}`);
            setApprovedVersion(null);
            setOpenVersionsMenu(false);

        } catch (e) {
            console.error("Failed to delete publish:", e);
            setApprovedVersion(null);
        }
    };

    const publishVersion = async ()=> {
        if(!project || !mainPipeline || !publishedVersion)return;
        try{
            const res = await fetch(`${api_url}/projects/${project.id}/pipelines/
                ${mainPipeline.id}/versions/${publishedVersion.id}/push`, {
                method: "POST",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.detail?.[0]?.msg || data.detail || "Failed to publish pipeline";
                console.error(errorMsg);
                setErrorMessage(errorMsg);
                return;
            }

            const activatedVersion: Pipeline = { ...publishedVersion, is_active: true, commited_at: new Date() };
            const updatedVersion: Pipeline = { ...mainPipeline, is_active: false };

            handleSwitchingVersion(updatedVersion, activatedVersion);

            setConfirmMessage(`Version ${publishedVersion.name} has been successfully published to ${project?.project_name} repository`);
            setWarningMessage(`Previous pipeline ${mainPipeline?.name} can be found in version history.\nURL: ${project?.repo_url}`);
            setPublishedVersion(null);

        } catch (e) {
            console.error("Failed to delete publish:", e);
        }
    };

    const deleteVersion = async () => {
        if(!project || !mainPipeline || !deletedVersion)return;
        try{
            const res = await fetch(`${api_url}/projects/${project.id}
                /pipelines/${mainPipeline.id}/versions/${deletedVersion.id}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail 
                    || "Failed to delete version with id: " + deletedVersion.id);
                setDeletedVersion(null);
                return;
            }

            // if deleted pipeline is the active one
            console.log("deleted version id:", deletedVersion.id, "current version id:", version?.id)
            if(deletedVersion.id === version?.id){ setVersion(null);}

            setVersions(prev => prev.filter(pipeline => pipeline.id !== deletedVersion.id));
            setDeletedVersion(null);
            setDiscardChanges(true);

        } catch (e) {
            console.error("Failed to delete pipeline:", e);
            setDeletedVersion(null);
        }
    };

    const handleSelectAtEdit = () => {
        setVersion(selectedVersion);
        setDiscardChanges(true);
        setSelectedVersion(null);
    }

    return (
        <div className={styles.versionBar}>
            <div className={styles.topContainer}>
                <p className={styles.header}>Edit Versions of "{mainPipeline?.name}"</p>
                <button className={`${styles.returnIcon} ${gStyles.clickable}`} 
                    onClick={() => (setOpenVersionsMenu(false), setMainPipeline(null), setVersion(null))} title="Return">
                    <FaArrowRightLong />
                </button>
            </div>

            <div className={styles.searchContainer}>
                <input type="text" className={styles.searchBar} name="searchBar" value={query}
                    placeholder="Search..." onChange={(e) => setQuery(e.target.value)}/>
                <IoClose onClick={() => setQuery("")} className={`${styles.deleteTextIcon} ${gStyles.clickable}`}/>
            </div>

            {filteredVersions.length > 0 ? <>
                {filteredVersions.map((p, index) => (
                    <div key={index} className={`${styles.pipelineTab} 
                        ${(p.id === version?.id)? styles.active : gStyles.clickable}`}>

                        <p className={`${styles.pipelineName} ${version?.id !== p.id && gStyles.clickable}`}
                            onClick={() => {
                                version?.id !== p.id && (
                                    isEdit? (
                                        hasChanges? (
                                            setSelectAtEdit(true),
                                            setSelectedVersion(p),
                                            setQuestionMessage("Changing the current version will discard all changes"),
                                            setWarningMessage("Your unsaved changes cannot be recovered.")
                                        ) : (setVersion(p), setIsEdit(false))
                                    ) : setVersion(p)
                                    , console.log("Version Selected with id:", p?.id)
                                )
                            }}>{p.name}</p>

                        <div className={styles.pipelineBtns}>
                            <MdDeleteOutline title="Delete"
                                className={`${styles.icon} ${gStyles.clickable}`}
                                onClick={() => {
                                    setDeletedVersion(p),
                                    setQuestionMessage(`Do you want to delete version ${p.name} ?`),
                                    setWarningMessage("This action cannot be recovered, maybe download it before lost.")
                                }}/>

                            <HiOutlineUpload title="Publish"
                                className={`${styles.icon} ${gStyles.clickable}`}
                                onClick={() => {
                                    setPublishedVersion(p);
                                    setQuestionMessage(`Publish version ${p.name} to ${project?.project_name} repository ?`);
                                    setWarningMessage(`This will override the existing pipeline on repository with the same name.\n
                                        Current pipeline will be saved in version history.\nURL: ${project?.repo_url}`);
                                }}/>

                            <TbArrowBarRight title="Approve"
                                className={`${styles.icon} ${gStyles.clickable}`}
                                onClick={() => {
                                    setApprovedVersion(p);
                                    setQuestionMessage(`Approve version ${p.name}?`);
                                    setWarningMessage(`This version will be set as the active one.
                                        \n Current pipeline ${mainPipeline?.name} will be inserted in history instead.`);
                                }}/>

                            <HiOutlineDownload onClick={()=>downloadYaml(p)} title="Download File"
                                className={`${styles.icon} ${gStyles.clickable}`}/>
                        </div>
                    </div>
                ))}
            </> : <p className={styles.noPipelines}>No edits made to pipeline {mainPipeline?.name} found.</p>}

            {questionMessage &&
            <Popup
                btnText1={
                    selectedAtEdit ? "Discard"
                    : deletedVersion? "Delete"
                    : publishedVersion ? "Publish"
                    : approvedVersion ? "Approve"
                    : ""
                }
                btn1Action={
                    deletedVersion ? () => {
                        deleteVersion();
                    } : approvedVersion ? () => {
                        approveVersion();
                    } : selectedVersion ? () => {
                        handleSelectAtEdit();
                    } : publishedVersion ? () => {
                        publishVersion();
                    } : null
                }
                btnText2="Cancel"
                btn2Action={()=>{
                    setSelectedVersion(null);
                    setDeletedVersion(null);
                    setPublishedVersion(null);
                    setApprovedVersion(null);
                }}
                questionMessage={questionMessage}
                setQuestionMessage={setQuestionMessage}
                warningMessage={warningMessage}
                setWarningMessage={setWarningMessage}
            />}

            {(confirmMessage || errorMessage) && <Popup
                btnText1="Got it"
                confirmMessage={confirmMessage}
                setConfirmMessage={setConfirmMessage}
                errorMessage={errorMessage}
                setErrorMessage={setErrorMessage}
                popupRef={popupRef}
            />}
        </div>
    );
}

export default VersionsBar;
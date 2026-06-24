import gStyles from "../../global.module.css"
import styles from "./SideBar.module.css";
import logo from "../../assets/yaml_wizard_logo.png";
import { useAuth } from '../../Context/AuthContext';
import type { Session, Message } from "../../types";

import { useState, useEffect, useRef, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";

import { IoPerson } from "react-icons/io5";
import { FaSignOutAlt } from "react-icons/fa";
import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { MdDeleteOutline, MdChatBubbleOutline } from "react-icons/md";
import { FaHistory } from "react-icons/fa";
import { GoPerson } from "react-icons/go";
import { RiDashboardFill } from "react-icons/ri";
import { Popup } from "../Popup/Popup";


type sideBar_props = {
    sessionId: number | null,
    setSessionId: React.Dispatch<React.SetStateAction<number | null>>,
    sessions: Session[],
    setSessions: React.Dispatch<React.SetStateAction<Session[] | []>>,
    setMessages: React.Dispatch<React.SetStateAction<Message[] | []>>,
    isLoading: boolean
}

function SideBar({sessionId, setSessionId, sessions, setSessions, setMessages, isLoading}: sideBar_props) {
    const [confirmMessage, setConfirmMessage] = useState<string | null>("");
    const [warningMessage, setWarningMessage] = useState<string | null>("");
    const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
    const [openSettings, setOpenSettings] = useState<boolean>(false);

    const settingsRef = useRef<HTMLDivElement | null>(null);
    const avatarRef = useRef<HTMLDivElement | null>(null);
    const avatarIconRef = useRef<HTMLDivElement | null>(null);

    const { username, loading, logout } = useAuth();
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    //get all sessions
    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const res = await fetch(`${api_url}/chatbot/sessions`, {
                    credentials: "include"
                });
                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail);
                    return;
                }
                setSessions(data);
            } catch (e) {
                console.error("Failed to load sessions:", e);
            }
        };

        fetchSessions();
    }, []);

    // new session
    const startNewSession = async () => {
        if(isLoading) return;

        setSessionId(null);
        sessionStorage.removeItem("session_id");
        setMessages([]);
    };

    // get session by id to make active
    const loadSession = async (session_id: number) => {
        if(isLoading) return;
        
        try {
            const res = await fetch(`${api_url}/chatbot/sessions/${session_id}`, {
                credentials: "include"
            });
            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }
            setSessionId(session_id);
            sessionStorage.setItem("session_id", session_id.toString());
            setMessages(data.messages);

        } catch (e) {
            console.error("Failed to load session:", e);
        }
    };
    
    const deleteSession = async () => {
        try{
            const res = await fetch(`${api_url}/chatbot/sessions/${sessionToDelete}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }
            setSessions(prev => prev.filter(session => session.id !== sessionToDelete));

            // if deleted session is the active one
            if(sessionId === sessionToDelete){
                startNewSession();
            }

        } catch (e) {
            console.error("Failed to delete session:", e);
        }
    };
    
    // sort sessions 
    const sessionsSorted = useMemo(() => {
        return [...sessions].sort((a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )}, [sessions]);

    // persist sessionsId to stay on after refresh
    useEffect(() => {
        const currentSessionId = sessionStorage.getItem("session_id");

        if (currentSessionId) {
            setSessionId(Number(currentSessionId));
            loadSession(Number(currentSessionId));
        }
        else{
            sessionStorage.clear();
        }
    }, []);

    // Close options on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (settingsRef.current &&
                    !settingsRef.current.contains(e.target as Node) && 
                    ((avatarRef.current && 
                    !avatarRef.current.contains(e.target as Node)) ||
                    (avatarIconRef.current &&
                    !avatarIconRef.current.contains(e.target as Node)))) {
                    setOpenSettings(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

    return(<>
        <div className={`${styles.sideBar} ${isCollapsed ? styles.collapsed : styles.expanded}`}>
        {isCollapsed? (<>
            <LuPanelRightClose className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                onClick={() => setIsCollapsed(prev => !prev)} title={"Expand"}/>
            <img src={logo} alt="" onClick={() => navigate("/")} title="Go to home page"
                className={`${styles.logo} ${gStyles.clickable}`}/>
            <MdChatBubbleOutline className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    title={"New Chat"} onClick={startNewSession}/>
            <FaHistory className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                title="Go to version history" onClick={() => navigate("/history")}/>
            <RiDashboardFill className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                title={"Go to Dashboard"} onClick={() => navigate("/dashboard")}/>
            
            <div ref={avatarIconRef} className={styles.settingsContainer}>
                <GoPerson className={`${styles.username} ${gStyles.clickable}`} title={"Open Menu"}
                onClick={() => setOpenSettings(prev => !prev)}/>
                {openSettings &&
                    <div className={styles.settingsMenu} ref={settingsRef}>
                        <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                            <IoPerson/>
                            Profile
                        </Link>
                        <Link className={`${styles.option} ${gStyles.clickable}`} to="/"
                            onClick={() => logout()}>
                            <FaSignOutAlt/> Sign out
                        </Link>
                    </div>
                }
            </div>
        </>) : (<>
            <div className={styles.topContainer}>
                <div className={styles.appNameContainer}>
                    <img src={logo} alt="" className={`${styles.logo} ${gStyles.clickable}`}
                        title="Go to home page" onClick={() => navigate("/")}/>
                    <span className={`${styles.appName} ${gStyles.clickable}`} onClick={() => navigate("/")}
                        title="Go to home page">YAML Wizard</span>
                    <LuPanelLeftClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                        onClick={() => setIsCollapsed(prev => !prev)} title={"Collapse"}/>
                </div>

                <button className={`${styles.actionBtn} ${gStyles.clickable}`}
                    onClick={startNewSession} title={"New Chat"}>
                    <MdChatBubbleOutline/> New Chat
                </button>
                <Link className={`${styles.actionBtn} ${gStyles.clickable}`} to="/history"
                    title="Go to version history">
                    <FaHistory/> Version History
                </Link>
                <Link className={`${styles.actionBtn} ${gStyles.clickable}`} to="/dashboard"
                    title={"Go to Dashboard"}>
                    <RiDashboardFill/> Dashboard
                </Link>
            </div>

            <p className={styles.sessionStart}>Chats</p>
            <div className={styles.sessions}>
                {sessionsSorted.map((session: any) => (
                    <div key={session.id} className = {`${styles.session}
                        ${session.id === sessionId ? styles.active : gStyles.clickable}
                        ${(sessionToDelete && session.id === sessionToDelete) && styles.sessionToDelete}`}>
                        
                        <span onClick={() => loadSession(session.id)} 
                            title={session.session_name + " - " + new Date(session.updated_at).toLocaleString()}
                            className={styles.sessionName}>{session.session_name || "New Chat"} {/*selected project*/}
                        </span>
                        
                        <button className={`${styles.deleteIcon} ${gStyles.clickable}`}  title="Delete"
                            onClick={() => {
                                setSessionToDelete(session.id);
                                setConfirmMessage("Delete this conversation?");
                                setWarningMessage("This action cannot be undone");
                            }}>
                            <MdDeleteOutline/>
                        </button>
                    </div>
                ))}
            </div>
            <p className={styles.sessionEnd}/>

            <div className={styles.bottomContainer}>
                {!loading && (
                    username? (
                        <div ref={avatarRef} className={styles.settingsContainer}>
                            <button className={`${styles.username} ${gStyles.clickable}`} title={"Open Menu"}
                                onClick={() => setOpenSettings(prev => !prev)}>
                                <GoPerson/>{username}
                            </button>
                            {openSettings && 
                                <div className={styles.settingsMenu} ref={settingsRef}>
                                    <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                                        <IoPerson/>
                                        Profile
                                    </Link>
                                    <Link className={`${styles.option} ${gStyles.clickable}`} to="/"
                                        onClick={() => logout()}>
                                        <FaSignOutAlt/>
                                        Sign out
                                    </Link>
                                </div>
                            }
                        </div>
                    ) : (<>
                        <span className={styles.username}>
                            Guest Mode
                            <Link className={`${styles.signUpNow} ${gStyles.clickable}`} to="/login">
                                Sign up to save your chats!
                            </Link>
                        </span>
                </>))}
            </div>
        </>)}
        </div>

        {confirmMessage && (
            <Popup
                btnText1={"Delete"}
                btn1Action={deleteSession}
                btnText2={"Cancel"}
                btn2Action={() => setSessionToDelete(null)}
                confirmMessage={confirmMessage}
                setConfirmMessage={setConfirmMessage}
                warningMessage={warningMessage}
                setWarningMessage={setWarningMessage}
                errorMessage={null}
                setErrorMessage={null}
                popupRef={null}
            />
        )}
    </>)
}

export default SideBar;
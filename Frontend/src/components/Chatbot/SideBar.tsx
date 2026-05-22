import gStyles from "../../global.module.css"
import styles from "./SideBar.module.css";
import logo from "../../assets/yaml_wizard_logo.png";
import { useAuth } from '../../Context/AuthContext';
import { Settings } from "./Menus";
import type { Session, Message } from "../../types";

import { useState, useEffect, useRef, useMemo } from "react";
import { Link } from "react-router-dom";

import { LuPanelRightClose, LuPanelLeftClose } from "react-icons/lu";
import { MdDeleteOutline, MdChatBubbleOutline } from "react-icons/md";
import { FaHistory } from "react-icons/fa";
import { FiMenu } from "react-icons/fi";
import { GoPerson } from "react-icons/go";
import { RiDashboardFill } from "react-icons/ri";


type sideBar_props = {
    sessionId: number | null,
    setSessionId: React.Dispatch<React.SetStateAction<number | null>>,
    sessions: Session[],
    setSessions: React.Dispatch<React.SetStateAction<Session[] | []>>,
    setMessages: React.Dispatch<React.SetStateAction<Message[] | []>>,
    isLoading: boolean
}

function SideBar({sessionId, setSessionId, sessions, setSessions, setMessages, isLoading}: sideBar_props) {
    const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);
    const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
    const [openSettings, setOpenSettings] = useState<boolean>(false);

    const settingsRef = useRef<HTMLDivElement | null>(null);
    const settingsBtnRef = useRef<HTMLDivElement | null>(null);
    const settingsIconRef = useRef<HTMLDivElement | null>(null);

    const { username, loading } = useAuth();
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

    // get session by id
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
    
    const deleteSession = async (session_id: number) => {
        try{
            const res = await fetch(`${api_url}/chatbot/sessions/${session_id}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }
            setSessions(prev => prev.filter(session => session.id !== session_id));
            setSessionToDelete(null);

            // if deleted session is the active one
            if(sessionId === session_id){
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
        const currentSession = sessionStorage.getItem("session_id");

        if (currentSession) {
            setSessionId(Number(currentSession));
            loadSession(Number(currentSession));
        }
    }, []);

    // Close options on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (settingsRef.current &&
                    !settingsRef.current.contains(e.target as Node) && 
                    ((settingsBtnRef.current && 
                    !settingsBtnRef.current.contains(e.target as Node)) ||
                    (settingsIconRef.current &&
                    !settingsIconRef.current.contains(e.target as Node)))) {
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
        {isCollapsed? (
            <>
                <LuPanelRightClose className={`${styles.collapsedBtn} ${gStyles.clickable}`}
                    onClick={() => setIsCollapsed(prev => !prev)} title={"Expand"}/>
                <img src={logo} alt="Logo" className={styles.logo}/>
                <MdChatBubbleOutline className={`${styles.collapsedBtn} ${gStyles.clickable}`} title={"New Chat"}
                    onClick={startNewSession}/>
                <FaHistory className={`${styles.collapsedBtn} ${gStyles.clickable}`} title={"Version History"}/>
                
                <div ref={settingsIconRef} className={styles.settingsContainer}>
                    <FiMenu className={`${styles.collapsedBtn} ${gStyles.clickable}`} title={"Settings"}
                        onClick={() => {setOpenSettings(prev => !prev); console.log(openSettings);}}/>
                    {openSettings && <Settings settingsRef={settingsRef}/>}
                </div>
                
                <GoPerson className={`${styles.username} ${gStyles.clickable}`} title={"Profile"}/>
            </>
        ) : (<>
            <div className={styles.topContainer}>
                <div className={styles.appNameContainer}>
                    <img src={logo} alt="Logo" className={styles.logo}/>
                    <span className={styles.appName}>YAML Wizard</span>
                    <LuPanelLeftClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                        onClick={() => setIsCollapsed(prev => !prev)} title={"Collapse"}/>
                </div>

                <button className={`${styles.actionBtn} ${gStyles.clickable}`} onClick={startNewSession} title={"New Chat"}>
                    <MdChatBubbleOutline/> New Chat
                </button>
                <button className={`${styles.actionBtn} ${gStyles.clickable}`} title={"Version History"}>
                    <FaHistory/> History
                </button>
                <Link className={`${styles.actionBtn} ${gStyles.clickable}`} to="/dashboard" title={"Open Dashboard"}>
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
                        
                        <button className={`${styles.deleteIcon} ${gStyles.clickable}`} 
                            onClick={() => setSessionToDelete(session.id)} title="Delete">
                            <MdDeleteOutline/>
                        </button>
                    </div>
                ))}
            </div>
            <p className={styles.sessionEnd}/>

            <div className={styles.bottomContainer}>
                <div ref={settingsBtnRef} className={styles.settingsContainer}>
                    <button className={`${styles.actionBtn} ${gStyles.clickable}`} 
                        onClick={() => setOpenSettings(prev => !prev)}>
                        <FiMenu/> Settings
                    </button>
                    {openSettings && <Settings settingsRef={settingsRef}/>}
                </div>

                {loading? null :
                    username? (
                        <Link className={`${styles.username} ${gStyles.clickable}`} to="/profile" title={"Profile"}>
                            <GoPerson/>{username}
                        </Link>
                    ) : (<>
                        <span className={styles.username}>
                            Guest Mode
                            <Link className={`${styles.signUpNow} ${gStyles.clickable}`} to="/login">
                                Sign up to save your chats!
                            </Link>
                        </span>
                </>)}
            </div>
        </>)}
        </div>

        {/* {openSettings && (
            <div className={styles.settingsMenu} ref={settingsRef}>
                <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                    <GoPerson/>
                    Profile
                </Link>
                <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={handleLogout}>
                    <FaSignOutAlt/>
                    Sign out
                </Link>
            </div>
        )} */}
        {sessionToDelete && (
            <div className={styles.popupLayover}>
                <div className={styles.deletePopup}>
                    <p className={styles.confirmMsg}>Delete this conversation?</p>
                    <p className={styles.warningMsg}>This action cannot be undone.</p>

                    <div className={styles.popupBtns}>
                        <button className={`${styles.deleteBtn} ${gStyles.clickable}`} onClick={() => deleteSession(sessionToDelete)}>
                            Delete
                        </button>

                        <button className={`${styles.deleteBtn} ${gStyles.clickable}`} onClick={() => setSessionToDelete(null)}>
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        )}
    </>)
}

export default SideBar;
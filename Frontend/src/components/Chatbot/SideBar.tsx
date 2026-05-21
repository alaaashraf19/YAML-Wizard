import gStyles from "../../global.module.css"
import styles from "./SideBar.module.css";
import logo from "../../assets/yaml_wizard_logo.png";
import type { Session, Message } from "../../types";

import { useState, useEffect, useRef, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';

import { LuPanelRightClose  } from "react-icons/lu";
import { MdDeleteOutline, MdChatBubbleOutline } from "react-icons/md";
import { FaHistory } from "react-icons/fa";
import { FiMenu } from "react-icons/fi";
import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";

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
    const [isCompact, setIsCompact] = useState<boolean>(false);
    const [openOptions, setOpenOptions] = useState<boolean>(false);
    const optionsRef = useRef<HTMLDivElement  | null>(null);
    const optionsButtonRef = useRef<HTMLButtonElement  | null>(null);
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
                if (optionsRef.current &&
                        !optionsRef.current.contains(e.target as Node) && 
                        optionsButtonRef.current && 
                        !optionsButtonRef.current.contains(e.target as Node)) {
                    setOpenOptions(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

    const handleLogout = async () => {
        try {
            const res = await fetch(`${api_url}/auth/logout`, {
                method: "POST",
                credentials: "include"
            });

            if (!res.ok){
                console.error("Logout failed");
                return;
            }

            logout();
            navigate("/login", { replace: true });
        } catch (err) {
            console.error("Server error:", err);
        }
    }

    return(<>
        <div className={`${styles.transition} ${isCompact ? styles.compact : styles.sideBar}`}>
        {isCompact? (<>
            <LuPanelRightClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                onClick={() => setIsCompact(prev => !prev)} title={"Expand"}/>
            <img src={logo} alt="Logo" className={styles.logo}/>
            <MdChatBubbleOutline className={gStyles.clickable} title={"New Chat"}
                onClick={startNewSession}/>
            <FaHistory className={gStyles.clickable} title={"Version History"}/>
            <FiMenu className={gStyles.clickable} title={"Settings"}/>
            <GoPerson className={`${styles.username} ${gStyles.clickable}`} title={"Profile"}/>
        </>) : (<>
            <div className={styles.topContainer}>
                <div className={styles.appNameContainer}>
                    <img src={logo} alt="Logo" className={styles.logo}/>
                    <span className={styles.appName}>YAML Wizard</span>
                    <LuPanelRightClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}
                        onClick={() => setIsCompact(prev => !prev)} title={"Collapse"}/>
                </div>

                <button className={`${styles.actionBtn} ${gStyles.clickable}`} onClick={startNewSession} title={"New Chat"}>
                    <MdChatBubbleOutline/> New Chat
                </button>
                <button className={`${styles.actionBtn} ${gStyles.clickable}`} title={"Version History"}>
                    <FaHistory/> History
                </button>
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
                <button className={`${styles.actionBtn} ${gStyles.clickable}`} 
                    onClick={() => setOpenOptions(prev => !prev)} ref={optionsButtonRef}>
                    <FiMenu/> Settings
                </button>
                {openOptions && (
                    <div className={styles.options} ref={optionsRef}>
                        <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                            <GoPerson/>
                            Profile
                        </Link>
                        <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={handleLogout}>
                            <FaSignOutAlt/>
                            Sign out
                        </Link>
                    </div>
                )}
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
import gStyles from "../../gobal.module.css"
import styles from "./SideBar.module.css";
import { useState, useEffect, useRef, useMemo } from "react";
import { LuPanelRightClose  } from "react-icons/lu";
import { MdDeleteOutline } from "react-icons/md";
import { MdChatBubbleOutline } from "react-icons/md";
import { FaHistory } from "react-icons/fa";


type Message = {
    role: "user" | "assistant",
    content: string,
    error?: boolean
};

type Session = {
    id: number | null;
    session_name: string;
    created_at: string;
    updated_at: string;
};

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
    const [sidebarWidth, setSidebarWidth] = useState(300);
    const isResizing = useRef(false);
    const api_url = import.meta.env.VITE_API_URL;
    
    // resize sidebar
    const startResizing = () => {
        isResizing.current = true;
    };
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing.current) return;
            var newWidth = e.clientX;

            // limits not working
            // if (newWidth < 150) newWidth = 200;
            // if (newWidth > 400) newWidth = 400;

            setSidebarWidth(newWidth);
        };
        const stopResizing = () => {
            isResizing.current = false;
        };

        window.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("mouseup", stopResizing);

        return () => {
            window.removeEventListener("mousemove", handleMouseMove);
            window.removeEventListener("mouseup", stopResizing);
        };
    }, []);

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
            console.log("data: ", data);

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

    return(<>
        <div className={styles.sideBar} style={{ width:sidebarWidth }}>
            <div className={styles.topContainer}>
                <div className={styles.appNameContainer}>
                    <LuPanelRightClose className={`${styles.closeBarBtn} ${gStyles.clickable}`}/>
                </div>

                <button className={`${styles.actionBtn} ${gStyles.clickable}`} onClick={startNewSession}>
                    <MdChatBubbleOutline/> New Chat
                </button>
                <button className={`${styles.actionBtn} ${gStyles.clickable}`}>
                    <FaHistory/> History
                </button>
            </div>
            <p className={styles.sectionStart}>Chats</p>
            <div className={styles.sessions}>
                {sessionsSorted.map((session: any) => (
                    <div key={session.id} className = {`${styles.session}
                        ${session.id === sessionId ? styles.active : gStyles.clickable}
                        ${(sessionToDelete && session.id === sessionToDelete) && styles.sessionToDelete}`}>
                        
                        <span onClick={() => loadSession(session.id)} title={new Date(session.updated_at).toLocaleString()}
                            className={styles.sessionName}>{session.session_name || "New Chat"}
                        </span>
                        
                        <button className={`${styles.deleteIcon} ${gStyles.clickable}`} 
                            onClick={() => setSessionToDelete(session.id)}>
                            <MdDeleteOutline/>
                        </button>
                    </div>
                ))}
            </div>
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

        <div className={styles.resizer} onMouseDown={startResizing}/>
    </>)
}

export default SideBar;
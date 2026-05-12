import gStyles from "../../gobal.module.css"
import styles from "./SideBar.module.css";
import { useState, useEffect, useRef, useMemo } from "react";
import { LuPanelRightClose  } from "react-icons/lu";


type Message = {
    role: "user" | "assistant",
    content: string
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
    setMessages: React.Dispatch<React.SetStateAction<Message[] | []>>
}

function SideBar({sessionId, setSessionId, sessions, setSessions, setMessages}: sideBar_props) {
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
        setSessionId(null);
        sessionStorage.removeItem("session_id");
        setMessages([]);
    };

    // get session by id
    const loadSession = async (session_id: number) => {
        try {
            const res = await fetch(`${api_url}/chatbot/sessions/${session_id}`, {
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                // console.error(data.detail);
                return;
            }

            setSessionId(session_id);
            sessionStorage.setItem("session_id", session_id.toString());
            setMessages(data.messages);

        } catch (e) {
            console.error("Failed to load session:", e);
        }
    };
    
    // sort sessions 
    const sessionsSorted = useMemo(() => {
        return [...sessions].sort((a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )}, [sessions]);

    // persist sessionsId to stay on after refresh
    useEffect(() => {
        const savedSession = sessionStorage.getItem("session_id");

        if (savedSession) {
            setSessionId(Number(savedSession));
            loadSession(Number(savedSession));
        }
    }, []);

    return(<>
        <div className={styles.sideBar} style={{ width:sidebarWidth }}>
            <LuPanelRightClose className={gStyles.clickable}/>
            <button className={styles.newChat} onClick={startNewSession}>New Chat</button>
            <p>Chats</p>
            <div className={styles.sessions}>
                {sessionsSorted.map((session: any) => (
                    <div key={session.id} onClick={() => loadSession(session.id)}
                        className = {`${styles.session} ${session.id === sessionId ? styles.active : gStyles.clickable}`}>
                        
                        {session.session_name}
                        <p></p>
                    </div>
                ))}
            </div>
        </div>

        <div className={styles.resizer} onMouseDown={startResizing}/>
    </>)
}

export default SideBar;
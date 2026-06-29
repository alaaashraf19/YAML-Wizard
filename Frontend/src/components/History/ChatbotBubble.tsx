import gStyles from "../../global.module.css"
import styles from "./ChatbotBubble.module.css"

import Popup from "../Popup/Popup";
import { useHistoryStore } from "../../pages/History";
import type { Message, Pipeline, Project, Session } from "../../types";
import { IoSend, IoClose } from "react-icons/io5";
import { useEffect, useRef, useState } from "react";
import { VscDebugRestart } from "react-icons/vsc";
import { RiRobot2Line } from "react-icons/ri";

type ChatbotBubbleProps = {
    isChatOpen: boolean,
    setIsChatOpen: React.Dispatch<React.SetStateAction<boolean>>
}

function ChatbotBubble({isChatOpen, setIsChatOpen }:ChatbotBubbleProps){
    const project: Project | null = useHistoryStore(s=>s.project);
    const pipeline: Pipeline | null = useHistoryStore(s=>s.pipeline);

    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<Message[] | []>([]);
    const [session, setSession] = useState<Session | null>(null);

    const [confirmMessage, setConfirmMessage] = useState<string | null>("");
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    const api_url = import.meta.env.VITE_API_URL;


    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        
        let userPrompt = prompt.trim();
        if (!userPrompt) return;

        const userMessage: Message = {
            role: "user",
            content: userPrompt
        };
        setMessages(prev => [...prev, userMessage]);
        setPrompt("");

        const sessionExist: boolean = session?true:false;

        console.log("at send, pipeline id:", pipeline?.id);
        setIsLoading(true);
        try{
            const res = await fetch(`${api_url}/chatbot/chat`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    message: userPrompt,
                    session_id: session?.id,
                    project_id: project?.id,
                    pipeline_id: pipeline?.id
                })
            })

            const data = await res.json();
            let text: string;
            
            if (!res.ok){
                console.error("Error with status code(", res.status, "):", data?.detail?.error);
                text = data.detail?.message?.content || "⚠️ Something went Wrong. Please try again later.";
            }
            else{
                text = data?.message?.content;
            }

            const botMessage: Message = {
                role: "assistant",
                content: text
            };
            setMessages(prev => [...prev, botMessage]);

            // Handle new session
            if (!sessionExist) {
                const newSession: Session = session ?? {
                    id: data.session_id || data.detail?.session_id,
                    session_name: data.session_name || data.detail?.session_name,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    pipeline: pipeline
                };
                setSession(newSession);
            }
            else{
                session && setSession({...session, updated_at: new Date().toISOString()});
            }

        } catch(e){
            console.error("Network/Server error:", e);

            const errMessage: Message = {
                role: "assistant",
                content: "⚠️ Cannot reach the server right now. Please check your connection and try again."
            };
            setMessages(prev => [...prev, errMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    //load session messages
    useEffect(() => {
        const loadSession = async () => {
            console.log("at load session pipeline is", pipeline?.id);
            try {
                const res = await fetch(`${api_url}/chatbot/sessions/by_pipeline/${pipeline?.id}`, {
                    credentials: "include"
                });
                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail);
                    return;
                }
                console.log("loaded session", data);
                const newSession: Session = {
                    id: data.id,
                    session_name: data.session_name,
                    created_at: data.created_at,
                    updated_at: data.updated_at,
                    pipeline: pipeline
                }
                setSession(newSession);
                setMessages(data.messages);
    
            } catch (e) {
                console.error("Failed to load session:", e);
            }
        };

        loadSession();
    }, [pipeline]);

    const deleteSession = async () => {
        try{
            const res = await fetch(`${api_url}/chatbot/sessions/${session?.id}`, {
                method: "DELETE",
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.error(data.detail);
                return;
            }
            setSession(null);
            setMessages([]);

        } catch (e) {
            console.error("Failed to delete session:", e);
        }
    };

    // Auto-scroll smoothly
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    //handle enter and shift+enter
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend(e);
        }
    };

    const isErrorMessage = (content: string) => {
        return content.startsWith("⚠️");
    };


    return( <div className={`${styles.chatbotWidget} ${ isChatOpen ? styles.chatbotOpen : styles.chatbotClosed}`}>
                {!isChatOpen ? (
                    <button className={styles.chatbotBubble} onClick={() => setIsChatOpen(true)} title="Open Chatbot">
                        {/* 🤖 */}<RiRobot2Line className={styles.botIcon}/>
                    </button>
                ) : (
                    <>
                        <div className={styles.chatbotHeader}>
                            <span className={styles.headerText}>Pipeline Assistant</span>
                            {session && <VscDebugRestart className={`${styles.chatbotBtn} ${gStyles.clickable}`}
                                onClick={() => session && setConfirmMessage("Reset this conversation?")}
                                title="Reset Chat"/>}
                            <IoClose className={`${styles.chatbotBtn} ${gStyles.clickable}`}
                                onClick={() => setIsChatOpen(false)} title="Close Chatbot"/> 
                        </div>

                        <div className={styles.chatMessages}>
                            <div className={styles.spacer}/>
                            {messages.map((msg, i) => (
                                <div key={i} className={styles.messagePack}>
                                    <p className={`${styles.message} ${msg.role === "user" ?
                                        styles.userMessage : (isErrorMessage(msg.content)? styles.errorMessage : styles.botMessage)}`}>
                                        {msg.content}
                                    </p>
                                </div>
                            ))}
                            {isLoading && (
                                <div className={`${styles.messagePack} ${styles.typing}`}>
                                    <div className={`${styles.typing_dot}`}></div>
                                    <div className={`${styles.typing_dot}`}></div>
                                    <div className={`${styles.typing_dot}`}></div>
                                </div>
                            )}
                            <div ref={messagesEndRef}/>
                        </div>

                        <div className={styles.chatbox}>
                            <form className={styles.form} onSubmit={handleSend}>
                                <textarea className={styles.textarea} placeholder="Ask anything .." name="prompt"
                                    rows={1} value={prompt} onChange={(e) => setPrompt(e.target.value)}
                                    onKeyDown={handleKeyDown} />

                                <button className={`${styles.sendButton} ${gStyles.clickable}`}
                                    type="submit" title="Send"> <IoSend/> </button>
                            </form>
                        </div>
                    </>
                )}

                {confirmMessage && (
                    <Popup
                        btnText1={"Reset"}
                        btn1Action={deleteSession}
                        btnText2={"Cancel"}
                        btn2Action={() => setSession(null)}
                        confirmMessage={confirmMessage}
                        setConfirmMessage={setConfirmMessage}
                    />
                )}
            </div>
            
        // </div>
    );
}

export default ChatbotBubble;
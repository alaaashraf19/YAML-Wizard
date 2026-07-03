import gStyles from "../global.module.css"
import styles from "./Chatbot.module.css";
import popupStyles from '../components/Popup/Popup.module.css'

import { useState, useEffect, useRef, useMemo } from "react";
import { MdOutlineKeyboardArrowRight } from "react-icons/md"
import { IoSend, IoClose } from "react-icons/io5";


import type { Session, Message, Project } from "../types";
import ChatProjects from "../components/Chatbot/ChatProjects";
import SideBar from "../components/Chatbot/SideBar";
import Popup from "../components/Popup/Popup";
import { ProjectSubInfo } from "../components/UserProfile/ProjectInfoTab";
import CodeBlock from "../components/Chatbot/CodeBlock";

export interface Model {
    id?: string,
    label: string,
    available?: boolean
}

function Chatbot() {
    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<Message[] | []>([]);
    const [sessionId, setSessionId] = useState<number | null>(null);
    const [sessions, setSessions] = useState<Session[]>([]);
    const [selectedProject, setSelectedProject] = useState<Project | null>(null);

    const [models, setModels] = useState<Model[]>([]);
    const [selectedModel, setSelectedModel] = useState<Model | null>(models[0]);

    const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
    const [isShowInfo, setIsShowInfo] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);
    const menuRef = useRef<HTMLDivElement | null>(null);
    const popupRef = useRef<HTMLDivElement | null>(null);
    const infoRef = useRef<HTMLDivElement | null>(null);
    // const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;
    let chat_url: string = 'chatbot/chat';

    // Auto focus on textarea
    useEffect(() => {
        textareaRef.current?.focus();
    }, []);
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const active = document.activeElement;
            const isTypingField =
                active instanceof HTMLInputElement ||
                active instanceof HTMLTextAreaElement;

            if (isTypingField) return;

            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                textareaRef.current?.focus();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => {window.removeEventListener("keydown", handleKeyDown)};
    }, []);

    // Close menu on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                    setIsMenuOpen(false);
                }
                if(infoRef.current && !infoRef.current.contains(e.target as Node)){
                    setIsShowInfo(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);

            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

    // Auto-scroll smoothly
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Control Textarea Height
    const MAX_HEIGHT = 300;
    const resizeTextarea = () => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        textarea.style.height = "auto";
        textarea.style.overflowY = "hidden";

        if(textarea.scrollHeight <= MAX_HEIGHT) {
            textarea.style.height = textarea.scrollHeight + "px";
        }
        else{
            textarea.style.height = MAX_HEIGHT + "px";
            textarea.style.overflowY = "auto";
        }
    };

    // Resize textarea on prompt change and window resize
    useEffect(() => {
        resizeTextarea();
    }, [prompt]);
    useEffect(() => {
        window.addEventListener("resize", resizeTextarea);

        return () => {
            window.removeEventListener("resize", resizeTextarea);
        };
    }, []);

    // get models
    useEffect(()=> {
        const fetchModels = async () => {
            try {
                const res = await fetch(`${api_url}/chatbot/models`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });

                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail || data.detail.msg || "Failed to load models");
                    return;
                }
                setModels(data.engines);

            } catch (e) {
                console.error("Failed to load models:", e);
            }
        }

        fetchModels();
    }, []);

    // get selected project on change of session id
    useEffect(() => {
        const foundProject = sessions.find(s => s.id === sessionId)?.project;
        setSelectedProject(foundProject ?? null);
    }, [sessionId, sessions]);

    //set text for select project button
    const selectedProjectText = useMemo(() => {
        return selectedProject? selectedProject.project_name :
            <span className={styles.connectBtn}> Connect Project
                <MdOutlineKeyboardArrowRight className={styles.arrow}/>
            </span>
    }, [selectedProject]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        const activeSessionId = sessionId;

        let userPrompt = prompt.trim();
        if (!userPrompt) return;

        const userMessage: Message = {
            role: "user",
            content: userPrompt
        };
        setMessages(prev => [...prev, userMessage]);

        textareaRef.current!.style.height = "auto";
        setPrompt("");

        // handle new session
        if (!activeSessionId) {
            const newSession: Session = {
                id: null,
                session_name: "...",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                project: selectedProject
            }

            setSessions(prev => [...prev, newSession]);
        }
        else {
            setSessions(prev => prev.map(s => s.id === activeSessionId
                ? { ...s, updated_at: new Date().toISOString() } : s));
        }

        setIsLoading(true);
        try{
            const res = await fetch(`${api_url}/${chat_url}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    message: userPrompt,
                    session_id: activeSessionId,
                    project_id: selectedProject?.id
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

            // Update session Id and name if it's a new session
            if (!activeSessionId) {
                const session_id = data.session_id || data.detail?.session_id;
                const session_name = data.session_name || data.detail?.session_name;

                setSessions(prev => prev.map(s => s.id === activeSessionId
                    ? { ...s, id: session_id, session_name: session_name } : s));

                setSessionId(session_id)
                sessionStorage.setItem("session_id", session_id.toString());
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

    const renderMessageContent = (content: string) => {
        const codeFenceRegex = /```(\w+)?\n?([\s\S]*?)```/g;
        const nodes: React.ReactNode[] = [];
        let lastIndex = 0;
        let match: RegExpExecArray | null;
        let key = 0;

        while ((match = codeFenceRegex.exec(content)) !== null) {
            if (match.index > lastIndex) {
                const textChunk = content.slice(lastIndex, match.index);
                if (textChunk.trim()) {
                    nodes.push(<span key={key++}>{renderBold(textChunk)}</span>);
                }
            }
            const language = match[1];
            const code = match[2].replace(/\n$/, "");
            nodes.push(<CodeBlock key={key++} language={language} code={code} />);
            lastIndex = codeFenceRegex.lastIndex;
        }

        if (lastIndex < content.length) {
            const textChunk = content.slice(lastIndex);
            if (textChunk.trim()) {
                nodes.push(<span key={key++}>{renderBold(textChunk)}</span>);
            }
        }

        return nodes.length ? nodes : renderBold(content);
    };

    const renderBold = (text: string) => {
        // const withoutBulletMarkers = text.replace(/^[ \t]*[*-][ \t]+/gm, "");
        const withoutBulletMarkers = text.replace(/^([ \t]*)[*-][ \t]+/gm, "$1");
        const parts = withoutBulletMarkers.split(/\*{1,2}(.*?)\*{1,2}/g);
        return parts.map((part, i) =>
            i % 2 === 1 ? <strong key={i}>{part}</strong> : part
        );
    };

    // get saved model from sessionStorage
    useEffect(() => {
        if (models.length === 0)return;
        console.log(typeof(models));

        const savedModelLabel = sessionStorage.getItem("selected_model");
        if (savedModelLabel) {
            const foundModel:Model | undefined = models.find(model => model.label === savedModelLabel);
            if (foundModel) {
                setSelectedModel(foundModel);
            }
        } else {
            setSelectedModel(models[0]);
            sessionStorage.setItem("selected_model", models[0]?.label);
        }
    }, [models, selectedModel]);


    const handleModelChange = (selectedModel: Model)=> {
        setSelectedModel(selectedModel);
        chat_url = selectedModel.label === "Main Model" ? 'chatbot/chat' : 'chatbot/generate'
    };


    return(
        <div className={styles.window}>
            <SideBar sessionId={sessionId} setSessionId={setSessionId} sessions={sessions}
                setSessions={setSessions} setMessages={setMessages} isLoading={isLoading}
                models={models} onModelChange={handleModelChange}/>

            <div className={styles.chatWindow}>
                <div className={styles.chatMessages}>
                    <div className={styles.spacer}/>
                    {messages.map((msg, i) => (
                        <div key={i} className={styles.messagePack}>
                            <div className={`${styles.message} ${msg.role === "user" ?
                                styles.userMessage : (isErrorMessage(msg.content)? styles.errorMessage : styles.botMessage)}`}>
                                {renderMessageContent(msg.content)}
                            </div>
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

                <div className={`${styles.inputContainer} ${messages.length === 0 ? styles.inputCenter : styles.inputBelow}`}>
                    {(messages.length === 0) &&
                        <p className={styles.emptyMessages}>
                            Start a conversation.
                        </p>
                    }
                    <div className={styles.chatbox}>

                        <form className={styles.form} onSubmit={handleSend}>
                            <textarea className={styles.textarea} placeholder="Ask anything .." name="prompt" rows={1}
                                ref = {textareaRef} value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown}>
                            </textarea>
                            <button className={`${styles.sendButton} ${gStyles.clickable}`} type="submit" title={"Send"}>
                                <IoSend/>
                            </button>
                        </form>

                        <div>
                            <button className={`${styles.projectButton} ${gStyles.clickable}`}
                                title={selectedProject ? "Show project info" : "Open projects menu"}
                                onClick={() => {!selectedProject? setIsMenuOpen(prev => !prev)
                                    : setIsShowInfo(true)
                                }}>
                                {selectedProjectText}
                            </button>
                            
                            {isShowInfo && 
                            <div className={popupStyles.popupLayover}>
                                <div className={`${styles.infoPopup} ${popupStyles.popup}`} ref={infoRef}>
                                    <div className={styles.infoBtns}>
                                        <IoClose className={`${gStyles.clickable} ${styles.infoBtn}`}
                                            onClick={() => setIsShowInfo(false)} title="Close"/>
                                    </div>
                                    <ProjectSubInfo selectedProject={selectedProject}/>
                                </div>
                            </div>
                            }

                            {isMenuOpen &&
                            <ChatProjects 
                                sessionId={sessionId}
                                setProject={setSelectedProject}
                                setSessions={setSessions}
                                setConfirmMessage={setConfirmMessage}
                                setErrorMessage={setErrorMessage}
                                setIsMenuOpen={setIsMenuOpen}
                                menuRef={menuRef}
                            />}
                        </div>
                    </div>
                </div>
            </div>

            {(confirmMessage || errorMessage) &&
            <Popup
                btnText1={"Got it"}
                confirmMessage={confirmMessage}
                setConfirmMessage={setConfirmMessage}
                errorMessage={errorMessage}
                setErrorMessage={setErrorMessage}
                popupRef={popupRef}
            />}
        </div>
    )
}

export default Chatbot;
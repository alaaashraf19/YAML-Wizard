import gStyles from "../../gobal.module.css"
import styles from "./Chatbot.module.css";
import { useState, useEffect, useRef } from "react";
import { MdOutlineKeyboardArrowRight } from "react-icons/md"
import Projects from "./Projects";
import SideBar from "./SideBar";


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

function Chatbot() {
    const [prompt, setPrompt] = useState("");
    const [menuOpen, setMenuOpen] = useState(false);
    const [messages, setMessages] = useState<Message[] | []>([]);
    const [sessionId, setSessionId] = useState<number | null>(null);
    const [sessions, setSessions] = useState<Session[]>([]);
    const [selectedProject, setSelectedProject] = useState<string | React.ReactNode>(<>
        Choose Project <MdOutlineKeyboardArrowRight style={{ marginLeft: 10 }} />
    </>);
    
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);
    const menuRef = useRef<HTMLDivElement | null>(null);
    const api_url = import.meta.env.VITE_API_URL;

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
                    setMenuOpen(false);
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
    

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();

        let userPrompt = prompt.trim();
        if (!userPrompt) return;

        const userMessage: Message = {
            role: "user",
            content: userPrompt
        };
        setMessages(prev => [...prev, userMessage]);

        textareaRef.current!.style.height = "auto";
        setPrompt("");

        try{
            const res = await fetch(`${api_url}/chatbot/chat`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({
                    message: userPrompt,
                    session_id: sessionId
                })
            })

            const data = await res.json();

            if (!sessionId) {
                console.log("session name is: ", data);
                const newSession = {
                    id: data.session_id,
                    session_name: data.session_name,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                }

                setSessions(prev => [...prev, newSession]);
                setSessionId(data.session_id)
                sessionStorage.setItem("session_id", data.session_id.toString());
            }
            else {
                setSessions(prev => prev.map(s => s.id === sessionId
                        ? { ...s, updated_at: new Date().toISOString() } : s));
            }

            let text = "";
            if (!res.ok){
                console.error("Error:", data.detail.error);
                text = data.detail?.message || "Something went Wrong. Please try again later.";
            }
            else{
                text = data.message.content;
            }

            const botMessage: Message = {
                role: "assistant",
                content: text
            };
            setMessages(prev => [...prev, botMessage]);

        }catch(e){
            console.error("Network/Server error:", e);

            const errMessage: Message = {
                role: "assistant",
                content: "Cannot reach the server right now. Please check your connection and try again."
            };
            setMessages(prev => [...prev, errMessage]);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend(e);
        }
    };

    return(
        <div className={styles.window}>
            <SideBar sessionId={sessionId} setSessionId={setSessionId} sessions={sessions} setSessions={setSessions} setMessages={setMessages}/>

            <div className={styles.chatWindow}>
                <div className={styles.chatMessages}>
                    <>
                    <div className={styles.spacer}/>
                    {messages.map((msg, i) => (
                        <div key={i} className={styles.messagePack}>
                            <p className={`${styles.message} ${msg.role === "user" ? styles.userMessage : styles.botMessage}`}>
                                {msg.content}
                            </p>
                        </div>
                    ))}
                    </>
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
                            <textarea className={styles.textarea} placeholder="Ask Anything.." name="prompt" rows={1}
                                ref = {textareaRef} value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown}>
                            </textarea>
                            <button className={`${styles.sendButton} ${gStyles.clickable}`} type="submit">Send</button>
                        </form>

                        <div>
                            <button onClick={() => setMenuOpen(prev => !prev)} className={`${styles.projectButton} ${gStyles.clickable}`}>
                                {selectedProject}
                            </button>

                            {menuOpen && <Projects setMenuOpen={setMenuOpen} setSelectedProject={setSelectedProject} menuRef={menuRef}/>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Chatbot;
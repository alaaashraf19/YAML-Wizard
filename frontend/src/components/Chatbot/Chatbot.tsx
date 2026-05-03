import gStyles from "../../gobal.module.css"
import styles from "./Chatbot.module.css";
import { useState, useEffect, useRef } from "react";
import { MdOutlineKeyboardArrowRight } from "react-icons/md"
import Projects from "./Projects";


function Chatbot() {
    type Message = {
        prompt: string;
        response: string;
    };

    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    // const [messages, setMessages] = useState<Message[]>([{"prompt": "Hello, how can I help you?", "response": "I'm here to assist you!"}]);

    const [selectedProject, setSelectedProject] = useState<string | React.ReactNode>(<>
        Choose Project <MdOutlineKeyboardArrowRight style={{ marginLeft: 10 }} />
    </>);
    const [menuOpen, setMenuOpen] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);
    const menuRef = useRef<HTMLButtonElement | null>(null);

    // Auto focus
    useEffect(() => {
        textareaRef.current?.focus();
    }, []);

    const handleBlur = (e: React.FocusEvent<HTMLTextAreaElement>) => {
        const next = e.relatedTarget as HTMLElement | null;

        if (!next || next.tagName !== "INPUT") {
            textareaRef.current?.focus();
        }
    };
    
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

    const MAX_HEIGHT = 300;

    // Control Textarea Height
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
    

    const handleSend = (e: React.FormEvent) => {
        e.preventDefault();

        let userPrompt = prompt.trim();
        if (!userPrompt) return;

        const response = "Response goes here";
        
        setMessages(prev => [
            ...prev,
            { prompt: userPrompt, response }
        ]);

        textareaRef.current!.style.height = "auto";
        setPrompt("");
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend(e);
        }
    };
    
    return(
        <div className={styles.chatWindow}>
            <div className={styles.chatMessages}>
                {messages.length === 0? (
                    <p className={styles.emptyMessages}>
                        Start a conversation.
                    </p>
                ) : (<>
                    <div className={styles.spacer}/>
                    {messages.map((msg, i) => (
                        <div key={i} className={styles.messagePack}>
                            <p className={`${styles.message} ${styles.userMessage}`}>
                                {msg.prompt}
                            </p>
                            <p className={`${styles.message} ${styles.botMessage}`}>
                                {msg.response}
                            </p>
                        </div>
                    ))}
                </>)}
                <div ref={messagesEndRef}/>
            </div>

            <div className={`${styles.chatbox} ${messages.length === 0 ? styles.chatboxCenter : styles.chatboxBelow}`}>
                <form className={styles.form} onSubmit={handleSend}>
                    <textarea className={styles.textarea} placeholder="Ask Anything.." name="prompt" rows={1} onBlur={handleBlur}
                        ref = {textareaRef} value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown}>
                    </textarea>
                    <button className={`${styles.sendButton} ${gStyles.clickable}`} type="submit">Send</button>
                </form>

                <div>
                    <button onClick={() => setMenuOpen(prev => !prev)} className={`${styles.projectButton} ${gStyles.clickable}`} ref={menuRef}>
                        {selectedProject}
                    </button>

                    {menuOpen && <Projects setMenuOpen={setMenuOpen} setSelectedProject={setSelectedProject} />}
                </div>
            </div>
        </div>
    )
}

export default Chatbot;
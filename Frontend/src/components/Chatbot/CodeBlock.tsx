import { useState } from "react";
import { IoCopyOutline, IoCheckmark, IoDownloadOutline, IoSunnyOutline, IoMoonOutline } from "react-icons/io5";
import styles from "./CodeBlock.module.css";

type CodeBlockProps = {
    language?: string;
    code: string;
    editable?: boolean;
    onChangeCode?: (value: string) => void;
    compact?: boolean;
};

// map common language names to file extensions for the download button
const extensionMap: Record<string, string> = {
    python: "py", py: "py",
    javascript: "js", js: "js",
    typescript: "ts", ts: "ts",
    tsx: "tsx", jsx: "jsx",
    yaml: "yml", yml: "yml",
    json: "json",
    bash: "sh", shell: "sh", sh: "sh",
    html: "html", css: "css",
    sql: "sql", java: "java",
    go: "go", c: "c", cpp: "cpp", "c++": "cpp",
    rust: "rs", php: "php",
};

function CodeBlock({ language, code, editable = false, onChangeCode, compact = false }: CodeBlockProps) {
    const [copied, setCopied] = useState(false);
    const [isLight, setIsLight] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch (e) {
            console.error("Copy failed:", e);
        }
    };

    const handleDownload = () => {
        const ext = language ? (extensionMap[language.toLowerCase()] || language.toLowerCase()) : "txt";
        const blob = new Blob([code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `snippet.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    return (
        <div className={`${styles.codeBlock} ${compact ? styles.compact : ""} ${isLight ? styles.light : ""}`}>
            <div className={styles.codeHeader}>
                <span className={styles.language}>{language || "text"}</span>
                <div className={styles.actions}>
                    <button className={styles.iconBtn} onClick={handleDownload} title="Download" type="button">
                        <IoDownloadOutline />
                    </button>
                    <button className={styles.iconBtn} onClick={handleCopy} title="Copy" type="button">
                        {copied ? <IoCheckmark className={styles.copied} /> : <IoCopyOutline />}
                    </button>
                </div>
            </div>
            {editable ? (
                <textarea
                    className={`${styles.codeContent} ${styles.codeTextarea}`}
                    value={code}
                    spellCheck={false}
                    onChange={(e) => onChangeCode?.(e.target.value)}
                />
            ) : (
                <pre className={styles.codeContent}>
                    <code>{code}</code>
                </pre>
            )}

            <div className={styles.codeFooter}>
                <button className={styles.themeToggleBtn} onClick={() => setIsLight((prev) => !prev)}
                    title={isLight ? "Switch to dark theme" : "Switch to light theme"} type="button">
                    {isLight ? <IoMoonOutline /> : <IoSunnyOutline />}
                    {isLight ? "Dark" : "Light"}
                </button>
            </div>
        </div>
    );
}

export default CodeBlock;
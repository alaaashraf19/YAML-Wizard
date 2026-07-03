import { useState } from "react";
import { IoCheckmarkCircle, IoCreateOutline } from "react-icons/io5";
import styles from "./PipelineApproval.module.css";
import CodeBlock from "./CodeBlock";

type PipelineApprovalProps = {
    code: string;
    language?: string;
    projectId?: number | null;
    branch?: string | null;
    apiUrl: string;
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>;
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>;
};

type Status = "idle" | "saving" | "approved";

function PipelineApproval({
    code,
    language,
    projectId,
    branch,
    apiUrl,
    setConfirmMessage,
    setErrorMessage,
}: PipelineApprovalProps) {
    const [draftCode, setDraftCode] = useState(code);
    const [isEditing, setIsEditing] = useState(false);
    const [status, setStatus] = useState<Status>("idle");

    const handleToggleEdit = () => {
        // finishing an edit re-enables Approve; if the pipeline was already
        // approved and the user edits again, treat it as a fresh, unapproved draft
        if (isEditing) {
            setStatus("idle");
        }
        setIsEditing(prev => !prev);
    };

    const handleApprove = async () => {
        if (isEditing || status === "saving") return;

        if (!projectId) {
            setErrorMessage("Connect a project first so this pipeline can be saved.");
            return;
        }

        setStatus("saving");
        try {
            const res = await fetch(`${apiUrl}/pipelines/${projectId}/approve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({
                    name: "generated-pipeline", // overridden server-side from the yaml's own name
                    description: "",
                    branch: branch || "main",
                    content: draftCode,
                    is_generated_by_wizard: true,
                }),
            });

            const data = await res.json().catch(() => ({}));

            if (!res.ok) {
                const message =
                    data?.detail?.message || data?.detail || "Failed to save the pipeline. Please try again.";
                throw new Error(typeof message === "string" ? message : JSON.stringify(message));
            }

            setStatus("approved");
            setConfirmMessage("Pipeline approved and saved to your project.");
        } catch (e) {
            console.error("Approve pipeline failed:", e);
            setStatus("idle");
            setErrorMessage(e instanceof Error ? e.message : "Failed to save the pipeline. Please try again.");
        }
    };

    return (
        <div className={styles.wrapper}>
            <CodeBlock
                language={language}
                code={draftCode}
                editable={isEditing}
                onChangeCode={setDraftCode}
            />

            <div className={styles.actionsBar}>
                {status === "approved" && !isEditing ? (
                    <span className={styles.approvedBadge}>
                        <IoCheckmarkCircle /> Approved & Saved
                    </span>
                ) : (
                    <button
                        type="button"
                        className={`${styles.actionBtn} ${styles.approveBtn}`}
                        onClick={handleApprove}
                        disabled={isEditing || status === "saving"}
                        title={isEditing ? "Finish editing before approving" : "Save this pipeline to your project"}
                    >
                        {status === "saving" ? "Saving..." : "Approve"}
                    </button>
                )}

                <button
                    type="button"
                    className={`${styles.actionBtn} ${styles.editBtn} ${isEditing ? styles.editing : ""}`}
                    onClick={handleToggleEdit}
                    disabled={status === "saving"}
                >
                    <IoCreateOutline /> {isEditing ? "Done Editing" : "Edit"}
                </button>
            </div>
        </div>
    );
}

export default PipelineApproval;
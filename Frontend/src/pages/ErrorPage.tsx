import { Link } from "react-router-dom";
import { FaExclamationTriangle } from "react-icons/fa";
import gStyles from "../global.module.css"
import styles from "./ErrorPage.module.css";

export default function ErrorPage() {
    return (
        <div className={styles.container}>
            <div className={styles.card}>
                <FaExclamationTriangle className={styles.icon} />

                <h1 className={styles.title}>Something went wrong</h1>

                <p className={styles.description}>
                    The page you're looking for couldn't be loaded, or you may
                    not have permission to access it.
                </p>

                <div className={styles.actions}>
                    <button
                        className={`${styles.secondaryBtn} ${gStyles.gButton}`}
                        onClick={() => window.history.back()}
                    >
                        Go Back
                    </button>

                    <Link to="/" className={`${styles.secondaryBtn} ${gStyles.gButton}`}>
                        Home Page
                    </Link>
                </div>

                <span className={styles.code}>
                    Error Code: 404
                </span>
            </div>
        </div>
    );
}
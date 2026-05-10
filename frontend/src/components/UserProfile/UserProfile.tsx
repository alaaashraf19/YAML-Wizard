import styles from './UserProfile.module.css'
function UserProfile() {
    const api_url = "https://sprain-reiterate-cape.ngrok-free.dev";

    const handleConnectGithub = () => {
        window.location.href = `${api_url}/platform/github/connect`;
    };

    const handleConnectGitlab = () => {
        window.location.href = `${api_url}/platform/gitlab/connect`;
    };

    const handleInstallApp = () => {
        window.location.href = `${api_url}/github/install_app`;
    };

    return (
        <div className={styles.formContainer}>
            <p className={styles.header}>Profile</p>

            <form className={styles.section}>
                <p>Information</p>
                <label>
                    Name:
                    <input type="text" />
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.header}>Security</p>
                <label>
                    Password:
                    <input type="password" />
                </label>
                <label>
                    Confirm Password:
                    <input type="password" />
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.header}>Projects</p>
                <label>
                    Repository URL:
                    <input type="text" />
                    <button type="button" className={styles.clickable}>
                        Add Project
                    </button>
                </label>
            </form>

            {/* IMPORTANT: not a form anymore */}
            <div className={styles.section}>
                <p className={styles.header}>Connect Accounts</p>

                <p className={styles.header}>Connect to GitHub</p>
                <button onClick={handleConnectGithub} className={`${styles.clickable}`}>Connect with github account</button>
                <button onClick={handleInstallApp} className={`${styles.clickable}`}>Install app</button> 
                <button onClick={handleConnectGitlab} className={`${styles.clickable}`}>Connect with gitlab account</button>
            </div>
        </div>
    );
}

export default UserProfile;
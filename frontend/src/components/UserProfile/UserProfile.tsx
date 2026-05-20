import gStyles from "../../gobal.module.css"
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
                <p className={styles.subHeader}>Information</p>
                <label id='name' className={styles.label}>
                    Name: 
                    <input type="text" className={styles.input}/>
                </label>
                <label id='email' className={styles.label}>
                    Email: 
                    <input type="text" className={styles.input}/>
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.subHeader}>Security</p>
                <label id='password' className={styles.label}>
                    Password: 
                    <input type="password" className={styles.input}/>
                </label>
                <label id='confirm_password' className={styles.label}>
                    Confirm Password: 
                    <input type="password" className={styles.input}/>
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.subHeader}>Projects</p>
                <label id='repo_url' className={styles.label}>
                    Repository URL: 
                    <input type="text" className={styles.input}/>
                    <button className={`${gStyles.clickable}`}>Add Project</button>
                </label>
            </form>

            <div className={styles.section}>
                <p className={styles.subHeader}>Connect to GitHub</p>
                <button onClick={handleConnectGithub} className={`${gStyles.clickable}`}>Connect with github account</button>
                <button onClick={handleConnectGitlab} className={`${styles.clickable}`}>Connect with gitlab account</button>
                <button onClick={handleInstallApp} className={`${gStyles.clickable}`}>Install app</button> 
            </div>
        </div>
    );
}

export default UserProfile;
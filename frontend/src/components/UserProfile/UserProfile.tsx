import gStyles from "../../gobal.module.css"
import styles from './UserProfile.module.css'

function UserProfile() {
    const api_url = import.meta.env.API_URL;

    const handleInstallApp = async () => {
        try{
            const res = await fetch(`${api_url}/install_app`, {
                method: "GET",
                headers: {"Content-Type": "application/json"},
                credentials: "include"
            });

            const data = await res.json();

            if(!res.ok){
                const msg = data.detail?.msg || "Couldn't install app to github";
                console.log("Error: ", msg);
                return;
            }

            console.log("Server:", data.detil.msg);

        }catch(err: any){
            const msg = err?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            console.error("Server error:", msg);
        }
    }

    const handleConnectGithub = async () => {
        try{
            const res = await fetch(`${api_url}/connect`, {
                method: "GET",
                headers: {"Content-Type": "application/json"},
                credentials: "include"
            });

            const data = await res.json();

            if(!res.ok){
                const msg = data.detail?.msg || "Couldn't install app to github";
                console.log("Error: ", msg);
                return;
            }

            console.log("Server:", data.detil.msg);

        }catch(err: any){
            const msg = err?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            console.error("Server error:", msg);
        }
    }

    return(<>
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
                <button onClick={handleInstallApp} className={`${gStyles.clickable}`}>Install app</button> 
            </div>
        </div>
    </>)
}

export default UserProfile;
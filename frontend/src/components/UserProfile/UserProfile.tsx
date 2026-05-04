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
                <p>Information</p>
                <label id='name'>
                    Name: 
                    <input type="text" />
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.header}>Security</p>
                <label id='password'>
                    Password: 
                    <input type="password" />
                </label>
                <label id='confirm_password'>
                    Confirm Password: 
                    <input type="password" />
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.header}>Projects</p>
                <label id='repo_url'>
                    Repository URL: 
                    <input type="text" />
                    <button className={`${styles.clickable}`}>Add Project</button>
                </label>
            </form>

            <form className={styles.section}>
                <p className={styles.header}>Connect to GitHub</p>
                <button onSubmit={handleConnectGithub} className={`${styles.clickable}`}>Connect with github account</button>
                <button onSubmit={handleInstallApp} className={`${styles.clickable}`}>Install app</button> 
            </form>
        </div>
    </>)
}

export default UserProfile;
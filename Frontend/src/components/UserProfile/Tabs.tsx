import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'
import type { Project } from "../../types";

type ProfileProps = {
    username: string,
    email: string,
    setUsername: React.Dispatch<React.SetStateAction<string>>,
    setEmail: React.Dispatch<React.SetStateAction<string>>,
    handleUpdateProfile: (e: React.FormEvent) => Promise<void>
};

export function ProfileTab({ username, email, setUsername, setEmail, handleUpdateProfile }: ProfileProps) {
    return (
        <form className={styles.section} onSubmit={(e) => {e.preventDefault(); handleUpdateProfile(e);}}>
            <h1 className={styles.header}>Profile</h1>
            <label id='name' className={styles.label}>
                Name: 
                <input name='username' type="text" className={styles.input}
                value={username} onChange={(e) => setUsername(e.target.value)}/>
            </label>
            <label id='email' className={styles.label}>
                Email: 
                <input name='email' type="text" className={styles.input}
                value={email} onChange={(e) => setEmail(e.target.value)}/>
            </label>
            <button type="submit" className={`${gStyles.clickable}`}>Update Profile</button>
        </form>
    );
}

type SecurityProps = {
    password: string,
    confirmPassword: string,
    showPassword: boolean,
    setPassword: React.Dispatch<React.SetStateAction<string>>,
    setConfirmPassword: React.Dispatch<React.SetStateAction<string>>,
    setShowPassword: React.Dispatch<React.SetStateAction<boolean>>
};

export function SecurityTab({ password, confirmPassword, showPassword, setPassword, setConfirmPassword, setShowPassword }: SecurityProps) {
    return (
        <form className={styles.section}>
            <h1 className={styles.header}>Security</h1>
            <label id='password' className={styles.label}>
                Password: 
                <input name='password' type="password" className={styles.input}
                value={password} onChange={(e) => setPassword(e.target.value)}/>
            </label>
            <label id='confirm_password' className={styles.label}>
                Confirm Password: 
                <input name='confirm_password' type="password" className={styles.input}
                value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}/>
            </label>
            <button type="submit" className={`${gStyles.clickable}`}>Update Password</button>
        </form>
    );
}

type ProjectsProps = {
    projects: Project[],
    setProjects: React.Dispatch<React.SetStateAction<Project[]>>
};

export function ProjectsTab({ projects, setProjects }: ProjectsProps) {
    return(<>
            <h1 className={styles.header}>Projects</h1>

            {(projects.length > 0) ? (<>
                <ul className={styles.projectList}>
                </ul>
            </>) : (
                <p className={styles.noProjects}>No projects added yet.</p>
            )}

            <form className={styles.section}>
                <h1 className={styles.header}>Add a project</h1>
                <label id='project_name' className={styles.label}>
                    Project name: 
                    <input name='project_name' type="text" className={styles.input}/>
                </label>
                <label id='repo_url' className={styles.label}>
                    Repository URL: 
                    <input name='repo_url' type="text" className={styles.input}/>
                </label>

                <label id="platform_label">
                    Platform:
                    <input type="radio" id="github" name="platform" value="github"/>
                    <label id="github">GitHub</label>

                    <input type="radio" id="gitlab" name="platform" value="gitlab"/>
                    <label id="gitlab">GitLab</label>
                </label>

                <button type="submit" className={`${gStyles.clickable}`}>Add Project</button>
            </form>
    </>);
}
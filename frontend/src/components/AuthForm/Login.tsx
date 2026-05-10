import gStyles from "../../gobal.module.css"
import styles from './AuthForm.module.css';
import { useState } from "react";
import { UsernameField, PasswordField } from "./AuthForm";
import { Link } from 'react-router-dom';
import { useNavigate } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';

function Login(){
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [responseError, setResponseError] = useState("");
    const [emptyUsername, setEmptyUsername] = useState(false);
    const [emptyPassword, setEmptyPassword] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();
    const api_url = import.meta.env.API_URL;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setResponseError("");
        
        if (!username) setEmptyUsername(true);
        else setEmptyUsername(false);
        if (!password) setEmptyPassword(true);
        else setEmptyPassword(false);
        
        if (!username || !password) {
            return;
        }
        
        const userData = {
            username,
            password
        };
        
        setLoading(true);
        try {
            const res = await fetch(`https://sprain-reiterate-cape.ngrok-free.dev/auth/login`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify(userData)
            });
            
            const data = await res.json();
            
            if (!res.ok) {
                if(data.detail && Array.isArray(data.detail) && data.detail.length > 0) {
                    const msg = data.detail[0].msg || "Login failed";
                    setResponseError(msg);
                } else {
                    const msg = data.detail || "Login failed";
                    setResponseError(msg);
                }
                console.error("Form validation error:", data);
                return;
            }

            login(username);
            console.log("Server:", data.msg);
            navigate("/chatbot"); // Redirect to home page on successful login

        } catch (err: any) {
            const msg = err?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setResponseError(msg);
            console.error("Server error:", err);

        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.formContainer}>
            <h1>Login</h1>
            <form className={styles.form} onSubmit={handleSubmit}>
                {responseError && <p className={styles.error}>{responseError}</p>}

                <UsernameField username={username} setUsername={setUsername}
                    emptyUsername={emptyUsername} setEmptyUsername={setEmptyUsername}/>

                <PasswordField password={password} setPassword={setPassword} emptyPassword={emptyPassword}
                    setEmptyPassword={setEmptyPassword} showPassword={showPassword}
                    setShowPassword={setShowPassword} />

                <button type="submit" className={`${styles.submit} ${gStyles.clickable}`} disabled={loading}>
                    {loading ? "Logging In..." : "Login"}
                </button>
            </form>

            <p>Don't have an account? <Link className={`${styles.link} ${gStyles.clickable}`} to="/signup">Sign Up</Link></p>
        </div>
    )
}

export default Login;
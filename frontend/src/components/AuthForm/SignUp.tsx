import gStyles from "../../gobal.module.css"
import styles from './AuthForm.module.css';
import { useState } from "react";
import { UsernameField, EmailField, PasswordField, ConfirmPasswordField } from "./AuthForm";
import { Link } from 'react-router-dom';
import { useNavigate } from "react-router-dom";

function SignUp(){
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [responseError, setResponseError] = useState("");
    const [emptyUsername, setEmptyUsername] = useState(false);
    const [emptyEmail, setEmptyEmail] = useState(false);
    const [emptyPassword, setEmptyPassword] = useState(false);
    const [emptyConfirmPassword, setEmptyConfirmPassword] = useState(false);
    const navigate = useNavigate();
    const api_url = import.meta.env.API_URL;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setResponseError("");
        
        if (!username) setEmptyUsername(true);
        else setEmptyUsername(false);
        if (!email) setEmptyEmail(true);
        else setEmptyEmail(false);
        if (!password) setEmptyPassword(true);
        else setEmptyPassword(false);
        if (!confirmPassword) setEmptyConfirmPassword(true);
        else setEmptyConfirmPassword(false);

        if (password !== confirmPassword)setResponseError("Passwords do not match.");
        
        if (!username || !email || !password || !confirmPassword 
            || password !== confirmPassword) {
            return;
        }
        
        
        const userData = {
            username,
            email,
            password
        };
        
        setLoading(true);
        try {
            const res = await fetch(`${api_url}/auth/signup`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(userData)
            });

            const data = await res.json();

            if (!res.ok) {
                const raw_message = data.detail?.[0]?.msg || "Signup failed";
                const msg = raw_message.replace("Value error, ", "");
                setResponseError(msg);
                console.error("Form validation error:", data);
                return;
            }

            console.log("Server:", data.msg);
            navigate("/login");

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
            <h1>Sign Up</h1>
            <form className={styles.form} onSubmit={handleSubmit} noValidate>
                {responseError && <p className={styles.error}>{responseError}</p>}
                <UsernameField username={username} setUsername={setUsername}
                    emptyUsername={emptyUsername} setEmptyUsername={setEmptyUsername}/>
                    
                <EmailField email={email} setEmail={setEmail} emptyEmail={emptyEmail}
                    setEmptyEmail={setEmptyEmail}/>
                {/* email doesn't have @ warning needs fixing */}

                <PasswordField password={password} setPassword={setPassword} emptyPassword={emptyPassword}
                    setEmptyPassword={setEmptyPassword} showPassword={showPassword}
                    setShowPassword={setShowPassword} />

                <ConfirmPasswordField confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword}
                    emptyConfirmPassword={emptyConfirmPassword} setEmptyConfirmPassword={setEmptyConfirmPassword}
                    showConfirmPassword={showConfirmPassword} setShowConfirmPassword={setShowConfirmPassword} />

                <button type="submit" className={`${styles.submit} ${gStyles.clickable}`} disabled={loading}>
                    {loading ? "Signing Up..." : "Sign Up"}
                </button>
            </form>

            <p>Already have an account? <Link className={`${styles.link} ${gStyles.clickable}`} to="/login">Login</Link></p>
        </div>
    )
}

export default SignUp;
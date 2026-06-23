import gStyles from "../global.module.css"
import styles from './SignUp.Login.module.css';
import { useState } from "react";
import { UsernameField, EmailField, PasswordField } from "../components/AuthForm/AuthForm";
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
    const api_url = import.meta.env.VITE_API_URL;

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
                console.error("Form validation error:", raw_message);
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
                <UsernameField username={username} setUsername={setUsername} editUsername={null} setEditUsername={null}/>
                {emptyUsername && <p className={styles.fieldError}>Username is required</p>}

                <EmailField email={email} setEmail={setEmail} editEmail={null} setEditEmail={null} />
                {emptyEmail && <p className={styles.fieldError}>Email is required</p>}

                <PasswordField type="Password" password={password} setPassword={setPassword}
                    showPassword={showPassword} setShowPassword={setShowPassword} />
                {emptyPassword && <p className={styles.fieldError}>Password is required</p>}

                <PasswordField type="Confirm Password" password={confirmPassword} setPassword={setConfirmPassword}
                    showPassword={showConfirmPassword} setShowPassword={setShowConfirmPassword} />
                {emptyConfirmPassword && <p className={styles.fieldError}>Confirm Password is required</p>}

                <button type="submit" className={`${styles.submit} ${gStyles.clickable}`} disabled={loading}>
                    {loading ? "Signing Up..." : "Sign Up"}
                </button>
            </form>

            <p>
                Already have an account?
                <Link className={`${styles.link} ${gStyles.clickable}`} to="/login">Login</Link>
            </p>
        </div>
    )
}

export default SignUp;
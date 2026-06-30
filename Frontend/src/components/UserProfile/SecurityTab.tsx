import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'

import { PasswordField } from "../AuthForm/AuthForm";
import { useState } from "react";

type SecurityProps = {
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>
};

function SecurityTab({ setConfirmMessage, setErrorMessage }: SecurityProps) {
    const [password, setPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    
    const api_url = import.meta.env.VITE_API_URL;

    // handle change password
    const handleNewPassword = async (e: React.FormEvent) => {
        e.preventDefault();

        const error = validatePasswordChange();
        if (error) {
            setErrorMessage(error);
            return;
        }
        setErrorMessage("");

        try {
            const res = await fetch(`${api_url}/user/profile`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({"current_password": password, "new_password": newPassword})
            });

            const data = await res.json();

            if (!res.ok) {
                const raw_message = data.detail?.[0]?.msg || data.detail || "Failed to change password";
                const msg = raw_message.replace("Value error, ", "");
                console.error(raw_message);
                setErrorMessage(msg);
                return;
            }
            setPassword("");
            setNewPassword("");
            setConfirmPassword("");

            setConfirmMessage("Password changed successfully");
            console.log("Password changed successfully");

        } catch (e: any){
            console.error("Failed to change password:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorMessage(msg);
        }
    };
    const validatePasswordChange = () : string | null => {
        if (newPassword !== confirmPassword){
            return "Confirmed Password does not match new password";
        }

        if (!password || !newPassword || !confirmPassword) {
            return "Some required fields are missing";
        }
        return null;
    };

    return (
        <form className={styles.form} onSubmit={(e) => {handleNewPassword(e);}}>
            <h1 className={styles.header}>Security</h1>
            <PasswordField 
                type="Current Password"
                password={password}
                setPassword={setPassword}
                showPassword={showPassword}
                setShowPassword={setShowPassword}
            />
            <PasswordField 
                type="New Password"
                password={newPassword}
                setPassword={setNewPassword}
                showPassword={showNewPassword}
                setShowPassword={setShowNewPassword}
            />
            <PasswordField
                type="Confirm Password"
                password={confirmPassword}
                setPassword={setConfirmPassword}
                showPassword={showConfirmPassword}
                setShowPassword={setShowConfirmPassword}
            />
            <button type="submit" className={`${gStyles.gButton} ${styles.button}`}>Change Password</button>
        </form>
    );
}

export default SecurityTab;
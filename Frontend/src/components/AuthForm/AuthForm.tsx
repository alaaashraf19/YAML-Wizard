import gStyles from "../../global.module.css"
import styles from './AuthForm.module.css';
import { FaEye, FaEyeSlash } from "react-icons/fa";
import { MdEdit } from "react-icons/md";
import { IoClose } from "react-icons/io5";
import { useState } from "react";

type UserNameProps = {
    username: string,
    setUsername: React.Dispatch<React.SetStateAction<string>>,
    editUsername: boolean | null,
    setEditUsername: React.Dispatch<React.SetStateAction<boolean>> | null
};

export function UsernameField(User_props: UserNameProps) {
    const [currUsername, setCurrUsername] = useState("");
    const showText = User_props.setEditUsername && !User_props.editUsername;
    return (
        <div className={styles.field}>
            <label id="username">
                <span className={styles.labelText}>Username:</span>
                {showText? (<>
                    <span>{User_props.username}</span>
                    <MdEdit title="Edit" className={`${styles.icon} ${gStyles.clickable}`}
                        onClick={() => {
                            User_props.setEditUsername && User_props.setEditUsername(true);
                            setCurrUsername(User_props.username);
                    }}/>
                </>) : (<>
                    <input type="text" className={styles.input} name='username'
                        placeholder="Enter username.." autoComplete="username"
                        value={User_props.username} onChange={(e) => {User_props.setUsername(e.target.value)}}>
                    </input>
                    {User_props.editUsername && (
                        <IoClose className={`${styles.icon} ${gStyles.clickable}`} title="Cancel"
                            onClick={() => {
                                User_props.setEditUsername && User_props.setEditUsername(false);
                                User_props.setUsername(currUsername);
                            }}/>
                    )}
                </>)}
            </label>
        </div>
    )
}

type EmailProps = {
    email: string,
    setEmail: React.Dispatch<React.SetStateAction<string>>,
    editEmail: boolean | null,
    setEditEmail: React.Dispatch<React.SetStateAction<boolean>> | null
};

export function EmailField(E_props: EmailProps) {
    const [currEmail, setCurrEmail] = useState("");
    const showText = E_props.setEditEmail && !E_props.editEmail;
    return (
        <div className={styles.field}>
            <label id='email'>
                <span className={styles.labelText}>Email:</span>
                {showText? (<>
                    <span>{E_props.email}</span>
                    <MdEdit title="Edit" className={`${styles.icon} ${gStyles.clickable}`}
                        onClick={() => {
                            E_props.setEditEmail && E_props.setEditEmail(true);
                            setCurrEmail(E_props.email);
                    }}/>
                </>) : (<>
                    <input type="email" className={styles.input} name='email' placeholder="Enter email.."
                        value={E_props.email} onChange={(e) => {E_props.setEmail(e.target.value)}}>
                    </input>
                    {E_props.editEmail && (
                        <IoClose className={`${styles.icon} ${gStyles.clickable}`} title="Cancel"
                            onClick={() => {
                                E_props.setEditEmail && E_props.setEditEmail(false);
                                E_props.setEmail(currEmail);
                            }}/>
                    )}
                </>)}
                
             </label>
        </div>
    )
}

type PasswordProps = {
    type: string,
    password: string,
    setPassword: React.Dispatch<React.SetStateAction<string>>
    showPassword: boolean,
    setShowPassword: React.Dispatch<React.SetStateAction<boolean>>
};

export function PasswordField(P_props: PasswordProps) {
    return(
        <div className={styles.field}>
            <label id={P_props.type}>
                <span className={styles.labelText}>{P_props.type}:</span>
                <div className={styles.passwordContainer}>
                    <input type={P_props.showPassword ? "text" : "password"} name={P_props.type} className={styles.input}
                        placeholder={`Enter ${P_props.type.toLowerCase()}..`} value={P_props.password} style={{width: "100%"}}
                        onChange={(e) => {P_props.setPassword(e.target.value)}}>
                    </input>
                    <button type="button" className={`${styles.toggle} ${gStyles.clickable}`} onClick={() => P_props.setShowPassword(!P_props.showPassword)}>
                        {P_props.showPassword ? <FaEye /> : <FaEyeSlash />}
                    </button>
                </div>
             </label>
        </div>
    )
}
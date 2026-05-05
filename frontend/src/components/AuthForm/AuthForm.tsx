import styles from './AuthForm.module.css';
import { FaEye, FaEyeSlash } from "react-icons/fa";

type UserNameProps = {
    username: string,
    setUsername: React.Dispatch<React.SetStateAction<string>>,
    emptyUsername: boolean,
    setEmptyUsername: React.Dispatch<React.SetStateAction<boolean>>
};

export function UsernameField(User_props: UserNameProps) {
    return (
        <div className={styles.field}>
            <label id="username">
                Username:
                <input type="text" className={styles.input} name='username' placeholder="Enter username.." autoComplete="username"
                    value={User_props.username} onChange={(e) => {User_props.setUsername(e.target.value); User_props.setEmptyUsername(false)}}>
                </input>
            </label>
            {User_props.emptyUsername && <p className={styles.fieldError}>Username is required</p>}
        </div>
    )
}

type EmailProps = {
    email: string,
    setEmail: React.Dispatch<React.SetStateAction<string>>,
    emptyEmail: boolean,
    setEmptyEmail: React.Dispatch<React.SetStateAction<boolean>>
};

export function EmailField(E_props: EmailProps) {
    return (
        <div className={styles.field}>
            <label id='email'>
                Email:
                <input type="email" className={styles.input} name='email' placeholder="Enter email.."
                    value={E_props.email} onChange={(e) => {E_props.setEmail(e.target.value); E_props.setEmptyEmail(false)}}>
                </input>
             </label>
            {E_props.emptyEmail && <p className={styles.fieldError}>Email is required</p>}
        </div>
    )
}

type PasswordProps = {
    password: string,
    setPassword: React.Dispatch<React.SetStateAction<string>>,
    emptyPassword: boolean,
    setEmptyPassword: React.Dispatch<React.SetStateAction<boolean>>,
    showPassword: boolean,
    setShowPassword: React.Dispatch<React.SetStateAction<boolean>>
};

export function PasswordField(P_props: PasswordProps) {
    return(
        <div className={styles.field}>
            <label id='password'>
                Password:
                <div className={styles.passwordContainer}>
                    <input type={P_props.showPassword ? "text" : "password"} name='password' className={styles.input}
                        placeholder="Enter password.." value={P_props.password}
                        onChange={(e) => {P_props.setPassword(e.target.value); P_props.setEmptyPassword(false)}}>
                    </input>
                    <button type="button" className={styles.toggle} onClick={() => P_props.setShowPassword(!P_props.showPassword)}>
                        {P_props.showPassword ? <FaEye /> : <FaEyeSlash />}
                    </button>
                </div>
             </label>
            {P_props.emptyPassword && <p className={styles.fieldError}>Password is required</p>}
        </div>
    )
}
type ConfirmPasswordProps = {
    confirmPassword: string,
    setConfirmPassword: React.Dispatch<React.SetStateAction<string>>,
    emptyConfirmPassword: boolean,
    setEmptyConfirmPassword: React.Dispatch<React.SetStateAction<boolean>>,
    showConfirmPassword: boolean,
    setShowConfirmPassword: React.Dispatch<React.SetStateAction<boolean>>
};

export function ConfirmPasswordField(CP_props: ConfirmPasswordProps) {
    return (
        <div className={styles.field}>
            <label id='confirmPassword'>
                Confirm Password:
                <div className={styles.passwordContainer}>
                    <input type={CP_props.showConfirmPassword ? "text" : "password"} name='confirmPassword'
                        className={styles.input} placeholder="Confirm password.." value={CP_props.confirmPassword}
                        onChange={(e) => {CP_props.setConfirmPassword(e.target.value); CP_props.setEmptyConfirmPassword(false)}}>
                    </input>
                    <button type="button" className={styles.toggle}
                        onClick={() => CP_props.setShowConfirmPassword(!CP_props.showConfirmPassword)}>
                        {CP_props.showConfirmPassword ? <FaEye /> : <FaEyeSlash />}
                    </button>
                </div>
             </label>
            {CP_props.emptyConfirmPassword && <p className={styles.fieldError}>Confirm Password is required</p>}
        </div>
    )
}
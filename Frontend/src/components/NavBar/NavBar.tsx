import gStyles from "../../global.module.css"
import styles from "./NavBar.module.css";
import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';
import { IoPerson } from "react-icons/io5";
import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";
import { FiMenu } from "react-icons/fi";


function NavBar(){
    const [openOptions, setOpenOptions] = useState<boolean>(false)
    const optionsRef = useRef<HTMLDivElement  | null>(null);
    const optionsButtonRef = useRef<HTMLButtonElement  | null>(null);
    const { username, loading, logout } = useAuth();
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

    // Close options on outside click
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (optionsRef.current &&
                        !optionsRef.current.contains(e.target as Node) && 
                        optionsButtonRef.current && 
                        !optionsButtonRef.current.contains(e.target as Node)) {
                    setOpenOptions(false);
                }
            }

            document.addEventListener("mousedown", handleClickOutside);
            return () => {
                document.removeEventListener("mousedown", handleClickOutside);
            };
        }
    , []);

    const handleLogout = async () => {
        try {
            const res = await fetch(`${api_url}/auth/logout`, {
                method: "POST",
                credentials: "include"
            });

            if (!res.ok){
                console.error("Logout failed");
                return;
            }

            logout();
            navigate("/login", { replace: true });

        } catch (err) {
            console.error("Server error:", err);
        }
    }

    return(
        <div className={styles.navBar}>
            {loading? null :
                username? (<>
                    <Link className={`${styles.username} ${gStyles.clickable}`} to="/profile">
                        <GoPerson/>{username}
                    </Link>
                    <Link className={`${styles.username} ${gStyles.clickable}`} to="/dashboard">
                    Dashboard
                    </Link>
                    <div className={styles.optionsContainer}>
                        <button className={`${styles.optionsButton} ${gStyles.clickable}`}  ref={optionsButtonRef}
                            onClick={() => setOpenOptions(prev => !prev)}>
                            <FiMenu/>        
                        </button>
                        {openOptions && (
                            <div className={styles.options} ref={optionsRef}>
                                <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                                    <IoPerson/>
                                    Profile
                                </Link>
                                <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={handleLogout}>
                                    <FaSignOutAlt/>
                                    Sign out
                                </Link>
                            </div>
                        )}
                    </div>
                    </>) : (<>
                        <Link className={`${styles.Link} ${styles.LoginLink} ${gStyles.clickable}`} to="/login">Login</Link>
                        <Link className={`${styles.Link} ${styles.SignUpLink} ${gStyles.clickable}`} to="/signup">Sign Up</Link>
                    </>)
            }
        </div>
    )
}

export default NavBar;
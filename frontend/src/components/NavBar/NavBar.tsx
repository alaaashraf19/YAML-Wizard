import gStyles from "../../gobal.module.css"
import styles from "./NavBar.module.css";
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';
import { IoPerson } from "react-icons/io5";
import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";

function NavBar(){
    const [openOptions, setOpenOptions] = useState<boolean>(false)
    const optionsRef = useRef<HTMLButtonElement  | null>(null);
    const { logout } = useAuth();
    const api_url = import.meta.env.API_URL;

    // Close options on outside click
    const username = sessionStorage.getItem("username");
    useEffect(
        () => {
            function handleClickOutside(e: MouseEvent) {
                if (optionsRef.current && !optionsRef.current.contains(e.target as Node)) {
                    setOpenOptions(false);
                }
            }

            document.addEventListener("click", handleClickOutside);
            return () => {
                document.removeEventListener("click", handleClickOutside);
            };
        }
    , []);

    const handleSignOut = () => {
        fetch(`${api_url}/auth/logout`, {
            method: "POST",
            credentials: "include"
        })
        .then(res =>  {
            if (!res.ok) throw new Error();
            return res.json();
        })
        .then(data => {
            logout();
            console.log("Server:", data.msg);
        })
        .catch((err) => {console.error("Server error:", err);})
    }

    return(
        <div className={styles.navBar}>
            {username? (<>
                <Link className={`${styles.username} ${gStyles.clickable}`} to="/profile">
                    <GoPerson/>{username}
                </Link>
                <Link className={`${styles.username} ${gStyles.clickable}`} to="/dashboard">
                Dashboard
                </Link>
                <div className={styles.optionsContainer}>
                    <button className={`${styles.optionsButton} ${gStyles.clickable}`} ref={optionsRef}
                        onClick={() => setOpenOptions(prev => !prev)}> ≡ </button>
                    {openOptions && (
                        <div className={styles.options}>
                            <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                                <IoPerson/>
                                Profile
                            </Link>
                            <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={handleSignOut}>
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
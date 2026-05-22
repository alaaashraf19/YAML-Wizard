import gStyles from "../../global.module.css"
import styles from "./NavBar.module.css";
import { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';
import { IoPerson } from "react-icons/io5";
import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";
import { FiMenu } from "react-icons/fi";


function NavBar(){
    const [openOptions, setOpenOptions] = useState<boolean>(false)
    const optionsRef = useRef<HTMLDivElement  | null>(null);
    const optionsButtonRef = useRef<HTMLButtonElement  | null>(null);
    const [showSettings, setShowSettings] = useState<boolean>(false);
    const [showUsername, setShowUsername] = useState<boolean>(false);
    const [showDashboard, setShowDashboard] = useState<boolean>(false);
    const [showChat, setShowChat] = useState<boolean>(false);
    const { username, loading, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
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

    // useEffect(() => {
    //     if (location.pathname === "/dashboard") {
    //         setShowSettings(true);
    //         setShowUsername(true);
    //         setShowChat(true);
    //         setShowDashboard(false);
    //     } 
    //     else if (
    //         location.pathname.startsWith("/profile") ||
    //         location.pathname === "/"
    //     ) {
    //         setShowUsername(true);
    //         setShowChat(true);
    //         setShowDashboard(true);
    //         setShowSettings(false);
    //     }
    // }, []);

    const isDashboard = location.pathname === "/dashboard";
    const isProfile = location.pathname.startsWith("/profile");
    const isHome = location.pathname === "/";

    return(
        <div className={styles.navBar}>
            {loading? null :
                username? (<>
                    {(isDashboard || isProfile || isHome) && <Link className={`${styles.username} ${gStyles.clickable}`} to="/chatbot">
                        Chat
                    </Link>}
                    
                    {(isProfile) && <Link className={`${styles.username} ${gStyles.clickable}`} to="/dashboard">
                        Dashboard
                    </Link>}

                    {(isDashboard || isProfile || isHome) && <Link className={`${styles.username} ${gStyles.clickable}`} to="/profile">
                        <GoPerson/>{username}
                    </Link>}

                    {(isDashboard || isProfile) && <div className={styles.optionsContainer}>
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
                    </div>}
                    </>) : (<>
                        <Link className={`${styles.Link} ${styles.LoginLink} ${gStyles.clickable}`} to="/login">Login</Link>
                        <Link className={`${styles.Link} ${styles.SignUpLink} ${gStyles.clickable}`} to="/signup">Sign Up</Link>
                    </>)
            }
        </div>
    )
}

export default NavBar;
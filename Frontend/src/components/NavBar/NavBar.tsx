import gStyles from "../../global.module.css"
import styles from "./NavBar.module.css";
import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';
import logo from "../../assets/yaml_wizard_logo.png";

import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";
import { FiMenu } from "react-icons/fi";


function NavBar(){
    const [openOptions, setOpenOptions] = useState<boolean>(false)
    const optionsRef = useRef<HTMLDivElement  | null>(null);
    const optionsButtonRef = useRef<HTMLButtonElement  | null>(null);
    const { username, loading, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

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


    const isDashboard = location.pathname === "/dashboard";
    const isHistory = location.pathname === "/history";
    const isProfile = location.pathname.startsWith("/profile");
    const isHome = location.pathname === "/" || location.pathname === "/home";

    return(
        <div className={styles.navBar}>
            {loading? null : (<>
                {(isProfile || isHome) && 
                    <img src={logo} alt="YAML Wizard" onClick={() => {if(!isHome)navigate("/")}}
                        className={`${styles.logo} ${styles.button} ${!isHome && gStyles.clickable}`}
                        title={isHome? "YAMLWizard" : "Go to home page"}/>
                }
                {username? (<>
                    {(isProfile || isHome || isHistory) &&
                    <Link className={`${styles.button} ${gStyles.gButton}`}
                        to="/dashboard" title="Go to dashboard">
                        Dashboard
                    </Link>}

                    {(isProfile || isHome || isDashboard) &&
                    <Link className={`${styles.button} ${gStyles.gButton}`}
                        to="/history" title="Go to version history">
                        Version History
                    </Link>}

                    {(isDashboard || isProfile || isHome || isHistory) &&
                    <Link className={`${styles.button} ${gStyles.gButton}`}
                        to="/chatbot" title="Go to chatbot">
                        Ask Chat
                    </Link>}

                    {(isDashboard || isHome || isHistory) &&
                    <Link className={`${styles.button} ${styles.username} ${gStyles.gButton}`}
                        to="/profile" title="Go to profile">
                        <GoPerson/>{username}
                    </Link>}

                    {(isDashboard || isProfile || isHome || isHistory) &&
                    <div className={styles.optionsContainer}>
                        <button className={`${styles.optionsButton} ${gStyles.clickable}`}  ref={optionsButtonRef}
                            onClick={() => setOpenOptions(prev => !prev)} title="Open Menu">
                            <FiMenu/>        
                        </button>
                        {openOptions && (
                            <div className={styles.options} ref={optionsRef}>
                                <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={() => logout()}>
                                    <FaSignOutAlt/>
                                    Sign out
                                </Link>
                            </div>
                        )}
                    </div>}
                </>) : (<>
                    <Link className={`${styles.Link} ${styles.LoginLink} ${gStyles.gButton}`} to="/login">Login</Link>
                    <Link className={`${styles.Link} ${styles.SignUpLink} ${gStyles.gButton}`} to="/signup">Sign Up</Link>
                </>)}
            </>)}
        </div>
    )
}

export default NavBar;
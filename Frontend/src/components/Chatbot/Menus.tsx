import gStyles from "../../global.module.css"
import styles from "./Menus.module.css";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from '../../Context/AuthContext';

import { GoPerson } from "react-icons/go";
import { FaSignOutAlt } from "react-icons/fa";

type SettingsProps = {
    settingsRef: React.RefObject<HTMLDivElement | null>;
};

export function Settings({ settingsRef }: SettingsProps) {
    const { logout } = useAuth();
    const navigate = useNavigate();
    const api_url = import.meta.env.VITE_API_URL;

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
        <div className={styles.settingsMenu} ref={settingsRef}>
            <Link className={`${styles.option} ${gStyles.clickable}`} to="/profile">
                <GoPerson/>
                Profile
            </Link>
            <Link className={`${styles.option} ${gStyles.clickable}`} to="/" onClick={handleLogout}>
                <FaSignOutAlt/>
                Sign out
            </Link>
        </div>
    )
}
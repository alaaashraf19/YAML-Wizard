import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'
import { useEffect, useState } from "react";

import { UsernameField, EmailField } from "../AuthForm/AuthForm";
import { GoPerson } from "react-icons/go";

type ProfileProps = {
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>
};

function ProfileTab({ setConfirmMessage, setErrorMessage } : ProfileProps) {
    const [currUsername, setCurrUsername] = useState("");
    const [username, setUsername] = useState("");
    const [currEmail, setCurrEmail] = useState("");
    const [email, setEmail] = useState("");

    const [editUsername, setEditUsername] = useState<boolean>(false);
    const [editEmail, setEditEmail] = useState<boolean>(false);
    const [profilePicture, setProfilePicture] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string>();
    const api_url = import.meta.env.VITE_API_URL;

    //get user info
    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const res = await fetch(`${api_url}/user/profile`, {
                    headers: {"Content-Type": "application/json"},
                    credentials: "include"
                });
                const data = await res.json();

                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to load profile");
                    return;
                }

                setCurrUsername(data.username);
                setUsername(data.username);

                setCurrEmail(data.email);
                setEmail(data.email);

            } catch (e) {
                console.error("Failed to load profile:", e);
            }
        };

        fetchProfile();
    }, []);
    
    // update profile info
    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();

        const error = validateProfileUpdate();
        if (error) {
            setErrorMessage(error);
            setUsername(currUsername);
            setEmail(currEmail);
            return;
        }
        setErrorMessage("");

        try{
            const res = await fetch(`${api_url}/user/profile`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                credentials: "include",
                body: JSON.stringify({"username": username, "email": email})
            });

            const data = await res.json();

            if (!res.ok) {
                const raw_message = data.detail?.[0]?.msg || data.detail || "Failed to update profile";
                const msg = raw_message.replace("Value error, ", "");
                console.error(raw_message);
                setErrorMessage(msg);
                setUsername(currUsername);
                setEmail(currEmail);
                return;
            }

            setUsername(username);
            setEmail(email);
            setCurrUsername(username);
            setCurrEmail(email);

            setConfirmMessage("Profile updated successfully");
            console.log("Profile updated successfully");

        }catch(e: any){
            console.error("Failed to update profile:", e);
            const msg = e?.response?.data?.detail?.[0]?.msg || "Server Error. Please try again later.";
            setErrorMessage(msg);
            setUsername(currUsername);
            setEmail(currEmail);
        }
    }
    const validateProfileUpdate = (): string | null => {
        if (!username || !email) {
            return "Some required fields are missing";
        }

        const newUsername = currUsername !== username ? username : undefined;
        const newEmail = currEmail !== email ? email : undefined;

        if (!newUsername && !newEmail) {
            return "No Change Detected";
        }
        return null;
    };

    //keep checking if there is a pic get its url
    useEffect(() => {
        if (!profilePicture) return;

        const url = URL.createObjectURL(profilePicture);
        setPreviewUrl(url);

        return () => URL.revokeObjectURL(url);
    }, [profilePicture]);

    //get user image
    useEffect(() => {
        const getImage = async () => {
            try {
                const res = await fetch(`${api_url}/user/avatar`, {
                    credentials: "include",
                    method: "GET",
                    headers: {"Content-Type": "application/json"}
                });
                
                const data = await res.json();
                
                if (!res.ok) {
                    console.error(data.detail?.[0]?.msg || data.detail || "Failed to get image");
                    return;
                }
                setPreviewUrl(data.avatar_url);
    
            } catch (e) {
                console.error("Failed to get image:", e);
            }
        }

        getImage();
    }, []);

    const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length)return;

        const file = e.target.files[0];
        const formData = new FormData();
        formData.append("file", file);
        try {

            const res = await fetch(`${api_url}/user/upload/avatar`, {
                credentials: "include",
                method: "POST",
                body: formData
            });
            
            const data = await res.json();
            
            if (!res.ok) {
                console.error(data.detail?.[0]?.msg || data.detail || "Failed to change image");
                return;
            }
            setProfilePicture(file);

        } catch (e) {
            console.error("Failed to change image:", e);
        }
    };

    return (<>
        <h1 className={styles.header}>Profile</h1>
        <div className={styles.profile}>
            <form className={`${styles.form} ${styles.profileSection}`}
                onSubmit={(e) => {handleUpdateProfile(e); setEditUsername(false); setEditEmail(false);}}>
                <UsernameField
                    username={username}
                    setUsername={setUsername}
                    editUsername={editUsername}
                    setEditUsername={setEditUsername}
                    />
                <EmailField
                    email={email}
                    setEmail={setEmail}
                    editEmail={editEmail}
                    setEditEmail={setEditEmail}
                    />
                {(editUsername || editEmail) && 
                    <button type="submit" className={`${gStyles.clickable} ${styles.button}`}>
                        Update Profile
                    </button>
                }
            </form>
            <div className={styles.imgContainer}>
                {previewUrl ? 
                <img className={styles.img} src={previewUrl} alt="Profile"/>
                :
                <GoPerson className={styles.img}/>
                }

                <div className={styles.imgBtnContainer}>
                    <label htmlFor="fileInput"
                        className={`${styles.inputImg} ${styles.button}  ${gStyles.clickable}`}>
                        Change Image
                    </label>
                    <input type="file" id="fileInput" accept="image/*" onChange={handleImageChange}
                        hidden/>
                </div>
            </div>
        </div>
    </>);
}

export default ProfileTab;
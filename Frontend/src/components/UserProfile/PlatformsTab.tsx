import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'

import type { Platform } from "../../types";
import { Platforms } from "../../types";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { VscDebugDisconnect } from "react-icons/vsc";
import { MdOutlineKeyboardArrowRight } from "react-icons/md"
import Popup from "../Popup/Popup";


type PlatformConnection = {
    connected: boolean;
    username: string | null;
};
type Repo = {
    name: string;
    url: string;
};
type Installation = {
    account_name: string;
    account_type: string;
    installation_id: string;
    repos_selection: string;
};

type PlatformsProps = {
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setWarningMessage: React.Dispatch<React.SetStateAction<string | null>>,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>
};

function PlatformsTab({ setConfirmMessage, setWarningMessage, setErrorMessage }: PlatformsProps){
    const [connections, setConnections] = useState<Partial<Record<Platform, PlatformConnection>>>({});
    const [repos, setRepos] = useState<Repo[]>([]);
    const [installations, setInstallations] = useState<Installation[]>([]);

    const [loadingPlatform, setLoadingPlatform] = useState<string>("");
    const [openInstalls, setOpenInstalls] = useState<boolean>(true);
    const [openRepos, setOpenRepos] = useState<boolean>(true);
    const [connectReturn, setConnectReturn] = useState<string | null>("");

    const [searchParams] = useSearchParams();
    const api_url = import.meta.env.VITE_API_URL;

    //check for url after connection to show popup
    useEffect(() => {
        console.log('SearchParams:', searchParams.toString()); // Debug log
        const platform = Platforms.find(p => searchParams.get(p) !== null);
        console.log('Found platform:', platform); // Debug log
        if (!platform) {
            console.log('No platform found in URL');
            return;
        }

        const connectionStatus = searchParams.get(platform);
        const reason = searchParams.get("reason");
        console.log('Status:', connectionStatus, 'Reason:', reason); // Debug log

        if (connectionStatus === "success") {
            console.log('Success! Posting message and setting confirm message');
            window.opener?.postMessage(
                { type: "connected" },
                window.location.origin
            );
            setConfirmMessage(`${platform.toUpperCase()} connected successfully`);
            // window.close();
        }

        if (connectionStatus === "error") {
            setErrorMessage(reason ?? `Failed to connect ${platform}.`);
        }
    }, [searchParams]);

    //check connected or not
    const checkConnected = async () => {
        try {
            const res = await fetch(`${api_url}/platform/integration/status`, {
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.log("Error:", data.detail);
                setConnections({});
                return;
            }

            setConnections(data);

        } catch (err) {
            console.error("Server error:", err);
            setConnections({});
        }
    };
    useEffect(() => {
        checkConnected();
    }, []);
    
    //get installed repos
    const getRepos = async () => {
        try {
            const res = await fetch(`${api_url}/github/installations/repos`, {
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.log("Error:", data.detail);
                setRepos([]);
                return;
            }

            setRepos(data.map((r: any) => ({
                name: r.repo_full_name,
                url: r.repo_url
            })));

        } catch (err) {
            console.error("Server error:", err);
            setRepos([]);
        }
    };
    useEffect(() => {
        getRepos();
    }, []);
    
    //get installations
    const getInstalls = async () => {
        try {
            const res = await fetch(`${api_url}/github/installations`, {
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.log("Error:", data.detail);
                setInstallations([]);
                return;
            }

            setInstallations(data.map((r: any) => ({
                account_name: r.account_login,
                account_type: r.account_type,
                installation_id: r.installation_id,
                repos_selection: r.repos_selection
            })));

        } catch (err) {
            console.error("Server error:", err);
            setInstallations([]);
        }
    };
    useEffect(() => {
        getInstalls();
    }, []);

    const handleConnectPlatfrom = (platform: Platform) => {
        setLoadingPlatform(platform);

        const url = `${api_url}/platform/${platform.toLowerCase()}/connect`;
        const newTab = window.open(url, "_blank", "noopener");

        // setTimeout(() => {
        //     window.open(url, "_blank", "noopener")
        // }, 100);

        const timer = setInterval(() => {
            if (newTab?.closed) {
                clearInterval(timer);
                checkConnected();
            }
        }, 500);

        setLoadingPlatform("");
    };
    //when the redirection comeback to this page
    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            if (event.origin !== window.location.origin) return;

            if (event.data.type === "connected") {
                console.log("Connection completed!");
                setConnectReturn("Connection Completed! You can close this window")
            }
        };

        window.addEventListener("message", handleMessage);

        return () => {
            window.removeEventListener("message", handleMessage);
        };
    }, []);
    
    const handleInstallApp = () => {
        setLoadingPlatform("install");

        const url = `${api_url}/github/install_app`;
        const newTab = window.open(url, "_blank", "noopener");

        setTimeout(() => {
            window.open(url, "_blank", "noopener")
        }, 100);

        const timer = setInterval(() => {
            if (newTab?.closed) {
                clearInterval(timer);
                getInstalls();
                getRepos();
            }
        }, 500);

        setLoadingPlatform("");
    };

    const handleDisconnectPlatfrom = async (platform: Platform) => {
        setLoadingPlatform(platform);
        try {
            const res = await fetch(`${api_url}/platform/${platform.toLowerCase()}/disconnect`, {
                credentials: "include"
            });

            const data = await res.json();

            if (!res.ok) {
                console.log("Error:", data.detail);
                setErrorMessage("Something is wrong with disconnecting right now");
                return;
            }
            setLoadingPlatform("");
            setConfirmMessage(`Disconnected from ${platform.toUpperCase()}`);
            setWarningMessage(`Disconnecting here won't revoke ${platform.toUpperCase()} authorization.\n`
                +`You can remove it later from ${platform.toUpperCase()} settings.`);
            checkConnected();
            
        } catch (err) {
            console.error("Server error:", err);
            setErrorMessage("Something is wrong with disconnecting right now");
        }
    };

    const handleDisconnectInstall = async (installation_id: string|null) => {
        let url = "";
        if(installation_id) url = `/${installation_id}`;
        else url = "";

        try {
            const res = await fetch(`${api_url}/github/disconnect${url}`, {
                method: "POST",
                credentials: "include",
                headers: {"Content-Type": "application/json"}
            });

            const data = await res.json();

            if (!res.ok) {
                console.log("Error:", data.detail);
                setErrorMessage("Something is wrong with disconnecting right now");
                return;
            }
            if(installation_id) setConfirmMessage(`Installation Removed`);
            else setConfirmMessage(`All Installations Removed`);

            getInstalls();
            getRepos();
            
        } catch (err) {
            console.error("Server error:", err);
            setErrorMessage("Something is wrong with disconnecting right now");
        }
    };

    return(
        <div className={styles.form}>
            <h1 className={styles.header}>Platforms</h1>

            {Platforms.map((platform, index) => (<div key={index}>
                <h2 className={styles.platformHeader}>{platform.toUpperCase()}</h2>
                <div className={styles.platform}>
                    {connections[platform]?.connected ? (
                        <div className={styles.platformSection}>
                            <label>Username:</label>
                            <p>{connections[platform]?.username}</p>
                            <button onClick={() => {handleDisconnectPlatfrom(platform); }}
                                className={`${gStyles.clickable} ${styles.button} ${styles.disconnectBtn}`}
                                disabled={loadingPlatform === platform} title={`Disconnect from ${platform}`}>
                                {loadingPlatform === platform ? "Connecting .." :`Disconnect`}
                            </button>
                        </div>
                    ) : (
                        <button onClick={() => {handleConnectPlatfrom(platform); }}
                            className={`${gStyles.gButton}`}
                            disabled={loadingPlatform === platform}>
                            {loadingPlatform === platform ? "Connecting .." :`Connect with ${platform} account`}
                        </button>
                    )}

                    {platform === "github" &&
                    <div className={styles.platformSection}>
                        <div className={`${styles.pSubSection} ${openInstalls && styles.expanded}`}>
                            <label className={styles.subSectionLabel} title="Open List"
                                onClick={() => setOpenInstalls(prev => !prev)}>
                                Your Installations
                                <span className={styles.arrow}> <MdOutlineKeyboardArrowRight
                                    className={`${openInstalls ? styles.arrowOpen : styles.arrowClose}`}/></span>
                            </label>

                            <ul className={styles.list}>
                                {installations.length > 0 ? (<>
                                    <li className={styles.subInfo}></li>
                                    {installations.map((ins, index) => (
                                        <li key={index}>
                                            <div className={styles.listItem}>
                                                <span className={styles.insAccName}>{ins.account_name}</span>
                                                {ins.repos_selection && 
                                                <span className={styles.subInfo} title="Selected or ALL">
                                                    {ins.repos_selection.toUpperCase()} Repos</span>}
                                                <span className={styles.subInfo} title="Account Owner">
                                                    {ins.account_type}</span>
                                                <button onClick={() => handleDisconnectInstall(ins.installation_id)}
                                                className={`${gStyles.clickable} ${styles.button} ${styles.disconnectIcon}`}
                                                title={`Disconnect ${ins.account_name}`}>
                                                    <VscDebugDisconnect/></button>
                                            </div>
                                        </li>
                                    ))}
                                    <button onClick={() => handleDisconnectInstall(null)}
                                    className={`${gStyles.clickable} ${styles.button} ${styles.disconnectBtn}`}>
                                        Disconnect All</button>
                                </>) : (<>
                                    <p className={styles.noProjects}>No insatallations yet.</p>
                                </>)}
                            </ul>
                        </div>

                        <div className={`${styles.pSubSection} ${openRepos && styles.expanded}`}>
                            <label className={styles.subSectionLabel} title="Open List"
                                onClick={() => setOpenRepos(prev => !prev)}>
                                Your Connected Repos
                                <span className={styles.arrow}> <MdOutlineKeyboardArrowRight
                                    className={`${openRepos ? styles.arrowOpen : styles.arrowClose}`}/></span>
                            </label>
                            
                            <ul className={styles.list}>
                                {repos.length > 0 ? (
                                    repos.map((repo, index) => (
                                        <li key={index} title={`Go to ${repo.url}`}>
                                            <div className={styles.listItem}>
                                                <Link to={repo.url} className={styles.link}>{repo.name}</Link>
                                            </div>
                                        </li>
                                    ))
                                ) : (
                                    <p className={styles.noProjects}>Install platform application to add repositories.</p>
                                )}
                            </ul>
                        </div>
                        <button onClick={handleInstallApp} className={`${gStyles.gButton}`}
                            title="Install app to add more repositories" disabled={loadingPlatform === "install"}>
                            {loadingPlatform === "install" ? "Connecting .." :"Install App & Manage Repos"}
                        </button>
                    </div>}
                </div>
            </div>))}
            {connectReturn && <Popup setConfirmMessage={setConnectReturn} />}
        </div>
    );
}

export default PlatformsTab;
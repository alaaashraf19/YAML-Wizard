import gStyles from "../../global.module.css"
import styles from './Tabs.module.css'

import type { Platform } from "../../types";
import { Platforms } from "../../types";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { VscDebugDisconnect } from "react-icons/vsc";
import { MdOutlineKeyboardArrowRight } from "react-icons/md"


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
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>>
};

function PlatformsTab({ setConfirmMessage, setErrorMessage }: PlatformsProps){
    const [connections, setConnections] = useState<Partial<Record<Platform, PlatformConnection>>>({});
    const [repos, setRepos] = useState<Repo[]>([]);
    const [installations, setInstallations] = useState<Installation[]>([]);
    const [loadingPlatform, setLoadingPlatform] = useState<string>("");
    const [openInstalls, setOpenInstalls] = useState<boolean>(false);
    const [openRepos, setOpenRepos] = useState<boolean>(false);

    const [searchParams] = useSearchParams();
    const api_url = import.meta.env.VITE_API_URL;

    //check for url after connection to show popup
    useEffect(() => {
        const platform = Platforms.find(p => searchParams.get(p) !== null);

        if (!platform) return;

        const connectionStatus = searchParams.get(platform);
        const reason = searchParams.get("reason");

        if (connectionStatus === "success") {
            setConfirmMessage(`${platform.toUpperCase()} connected successfully`);
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
        setTimeout(() => {
            window.location.href = `${api_url}/platform/${platform.toLowerCase()}/connect`;
        }, 100);
    };
    
    const handleInstallApp = () => {
        setLoadingPlatform("install");
        setTimeout(() => {
            window.location.assign(`${api_url}/github/install_app`);
        }, 100);
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
            setConfirmMessage(`Disconnected from ${platform}`);
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
            if(installation_id) setConfirmMessage(`Disconnected from installation`);
            else setConfirmMessage(`Disconnected from all installations`);

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
                                {loadingPlatform === platform ? "Redirecting .." :`Disconnect`}
                            </button>
                        </div>
                    ) : (
                        <button onClick={() => {handleConnectPlatfrom(platform); }}
                            className={`${gStyles.clickable} ${styles.button}`}
                            disabled={loadingPlatform === platform}>
                            {loadingPlatform === platform ? "Redirecting .." :`Connect with ${platform} account`}
                        </button>
                    )}

                    {platform === "github" &&
                    <div className={styles.platformSection}>
                        <div className={styles.p_SubSection}>
                            <label className={styles.subSectionLabel} title="Open List"
                                onClick={() => setOpenInstalls(prev => !prev)}>
                                Your Installations
                                <span className={styles.arrow}> <MdOutlineKeyboardArrowRight
                                    className={`${openInstalls ? styles.arrowOpen : styles.arrowClose}`}/></span>
                            </label>

                            {openInstalls && (
                            <ul className={styles.list}>
                                {installations.length > 0 ? (<>
                                    {installations.map((ins, index) => (
                                        <li key={index}>
                                            <div className={styles.listItem}>
                                                <span className={styles.insAccName}>{ins.account_name}</span>
                                                {ins.repos_selection && 
                                                <span className={styles.subInfo}>{ins.repos_selection.toUpperCase()} Repos</span>}
                                                <span className={styles.subInfo}>{ins.account_type}</span>
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
                                </>) : (
                                    <p className={styles.noProjects}>No insatallations yet.</p>
                                )}
                            </ul>)}
                        </div>

                        <div className={`${styles.p_SubSection} ${openRepos? styles.openSection : styles.closedSection}`}>
                            <label className={styles.subSectionLabel} title="Open List"
                                onClick={() => setOpenRepos(prev => !prev)}>
                                Your Connected Repos
                                <span className={styles.arrow}> <MdOutlineKeyboardArrowRight
                                    className={`${openRepos ? styles.arrowOpen : styles.arrowClose}`}/></span>
                            </label>
                            
                            {openRepos && (
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
                                    <p className={styles.noProjects}>No repositories connected yet.</p>
                                )}
                            </ul>)}
                        </div>
                        <button onClick={handleInstallApp} className={`${gStyles.clickable} ${styles.button}`}
                            title="Install app to add more repositories" disabled={loadingPlatform === "install"}>
                            {loadingPlatform === "install" ? "Redirecting .." :"Install App & Connect Repos"}
                        </button>
                    </div>}
                </div>
            </div>))}

            {/* {(errorMessage || confirmMessage) && 
                <Popup 
                    btnText1={"Got it"}
                    btn1Action={() => {navigate("/profile", { replace: true });}}
                    btnText2={null}
                    btn2Action={null}
                    confirmMessage={confirmMessage}
                    setConfirmMessage={setConfirmMessage}
                    warningMessage={null}
                    setWarningMessage={null}
                    errorMessage={errorMessage}
                    setErrorMessage={setErrorMessage}
                    popupRef={popupRef}
                />
            } */}
        </div>
    );
}

export default PlatformsTab;
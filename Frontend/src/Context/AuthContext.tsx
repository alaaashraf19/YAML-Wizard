import { createContext, useContext, useState, useEffect } from "react";
import type { AuthContextType } from "../types";


const AuthContext = createContext<AuthContextType | null>(null);

const GUEST_STORAGE_KEY = "isGuest";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [username, setUsername] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean | null>(true);
    // Guest is a deliberate, explicit choice ("Continue as Guest"), distinct
    // from simply not being logged in yet. Persisted in sessionStorage so it
    // survives a refresh, but never sent to / trusted by the backend - it's
    // purely a frontend UI flag for gating routes and features.
    const [isGuest, setIsGuest] = useState<boolean>(
        () => sessionStorage.getItem(GUEST_STORAGE_KEY) === "true"
    );
    const api_url = import.meta.env.VITE_API_URL;

    const login = (user: string) => {
        setUsername(user);
        setIsGuest(false);
        sessionStorage.removeItem(GUEST_STORAGE_KEY);
    };

    const loginAsGuest = () => {
        setUsername(null);
        setIsGuest(true);
        sessionStorage.setItem(GUEST_STORAGE_KEY, "true");
    };

    // Check logged in user constantly
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch(`${api_url}/auth/me`, {
                    credentials: "include"
                });

                const data = await res.json();

                if (!res.ok) {
                    console.log("Error:", data.detail);
                    setUsername(null);
                    return;
                }

                setUsername(data.username);
                setIsGuest(false);
                sessionStorage.removeItem(GUEST_STORAGE_KEY);

            } catch (err) {
                console.error("Server error:", err);
                setUsername(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const logout = async () => {
        try {
            const res = await fetch(`${api_url}/auth/logout`, {
                method: "POST",
                credentials: "include"
            });

            if (!res.ok){
                console.error("Logout failed");
                return;
            }

            setUsername(null);
            setIsGuest(false);
            sessionStorage.clear();
            localStorage.clear();
            window.location.href = "/";
            console.log("Logged out successfully");

        } catch (err) {
            console.error("Server error:", err);
        }
    };

    return (
        <AuthContext.Provider value={{ username, loading, isGuest, login, loginAsGuest, logout }}>
        {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
    return ctx;
}
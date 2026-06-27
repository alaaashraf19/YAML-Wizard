import { createContext, useContext, useState, useEffect } from "react";
import type { AuthContextType } from "../types";


const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [username, setUsername] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean | null>(true);
    const api_url = import.meta.env.VITE_API_URL;

    const login = (user: string) => {
        setUsername(user);
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
                    sessionStorage.clear();
                    localStorage.clear();
                    return;
                }

                setUsername(data.username);

            } catch (err) {
                console.error("Server error:", err);
                setUsername(null);
                sessionStorage.clear();
                localStorage.clear();
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

            window.location.href = "/";
            setUsername(null);
            console.log("Logged out successfully");

        } catch (err) {
            console.error("Server error:", err);
        }
    };

    return (
        <AuthContext.Provider value={{ username, loading, login, logout }}>
        {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
    return ctx;
}
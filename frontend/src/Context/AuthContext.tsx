import { createContext, useContext, useState, useEffect } from "react";

type AuthContextType = {
    username: string | null;
    loading: boolean | null;
    login: (username: string) => void;
    logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [username, setUsername] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean | null>(true);

    const login = (user: string) => {
        setUsername(user);
    };

    // Check logged in user constantly
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch("http://localhost:8000/auth/me", {
                    credentials: "include"
                });

                const data = await res.json();

                if (!res.ok) {
                    console.log("Error:", data);
                    setUsername(null);
                    return;
                }

                setUsername(data.username);

            } catch (err) {
                console.error("Server error:", err);
                setUsername(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const logout = () => {
        setUsername(null);
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
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../Context/AuthContext";
import type { LoginRedirectState } from "../../types";

type ProtectedRouteProps = {
    children: React.ReactNode;
    allowGuest?: boolean;
};

export function ProtectedGuest({ children, allowGuest = false }: ProtectedRouteProps) {
    const { username, isGuest, loading } = useAuth();
    const location = useLocation();

    if (loading) return null;

    const isAllowed = !!username || (allowGuest && isGuest);

    if (!isAllowed) {
        const state: LoginRedirectState = {
            from: { pathname: location.pathname + location.search },
            allowGuest
        };
        return <Navigate to="/login" state={state} replace />;
    }

    return <>{children}</>;
}
export function ProtectedUser({ children }: ProtectedRouteProps) {
    const { username, loading } = useAuth();
    if (loading) return null;


    if (username) {

        return <Navigate to="/"  replace />;
    }

    return <>{children}</>;
}

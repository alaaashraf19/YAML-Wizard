import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../Context/AuthContext";
import type { LoginRedirectState } from "../../types";

type ProtectedRouteProps = {
    children: React.ReactNode;
    // Whether a Guest (no account) is allowed on this route. Defaults to
    // false, meaning the route requires a real logged-in user - dashboard,
    // history, and profile all hold data that only exists for real
    // accounts, so a guest has nothing to see there anyway.
    allowGuest?: boolean;
};

function ProtectedRoute({ children, allowGuest = false }: ProtectedRouteProps) {
    const { username, isGuest, loading } = useAuth();
    const location = useLocation();

    // Wait for the initial /auth/me check to finish before deciding -
    // otherwise a real logged-in user would flash-redirect to /login on
    // every hard refresh while `username` is still null.
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

export default ProtectedRoute;

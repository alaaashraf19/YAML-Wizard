import Navbar from './components/NavBar/NavBar';
import { useEffect } from 'react';
import { Outlet, useLocation } from "react-router-dom";

function App() {
    const location = useLocation();

    useEffect(() => {
        if (!location.pathname.startsWith("/profile")) {
            sessionStorage.removeItem("project_id");
        }
    }, [location.pathname]);

    return (
        <>
        <Navbar />
        <Outlet />
        </>
    )
}

export default App

import Navbar from './components/NavBar/NavBar';
import { Outlet } from "react-router-dom";

function App() {

    return (
        <>
        <Navbar />
        <Outlet />
        </>
    )
}

export default App

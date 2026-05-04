import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './Context/AuthContext.tsx';
import App from './App.tsx'
import SignUp from './components/AuthForm/SignUp.tsx';
import Login from './components/AuthForm/Login.tsx';
import Chatbot from './components/Chatbot/Chatbot.tsx';
import UserProfile from './components/UserProfile/UserProfile.tsx';
import Connect from "./pages/Connect.tsx";

const router = createBrowserRouter([{
  element: <App />,
  children: [
    { path: "/chatbot", element: <Chatbot /> },
    { path: "/profile", element: <UserProfile/>},
    { path: "/connect", element: <Connect /> }, // ✅ ADD THIS

    { path: "/", element: <SignUp /> },
    // {path: "*", element: <App />}, // Handle not provided page
  ]},
  { path: "/signup", element: <SignUp /> },
  { path: "/login", element: <Login /> },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
)

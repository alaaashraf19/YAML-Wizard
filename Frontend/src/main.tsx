import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './Context/AuthContext.tsx';

import App from './App.tsx'
import SignUp from './pages/SignUp.tsx';
import Login from './pages/Login.tsx';
import Home from './pages/Home.tsx';
import Chatbot from './pages/Chatbot.tsx';
import UserProfile from './pages/UserProfile.tsx';
import Dashboard from './pages/Dashboard.tsx';
import History from './pages/History.tsx';
import Error from './pages/ErrorPage.tsx';


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
    },
  },
})


const router = createBrowserRouter([{
  element: <App />,
  errorElement: <Error/>,
  children: [
    { path: "/chatbot", element: <Chatbot/> },
    { path: "/profile", element: <UserProfile/>},
    { path: '/dashboard', element: <Dashboard/> },
    { path: '/history', element: <History/> },
    { path: "/", element: <Home/> },
    {path: "*", element: <Error/>}, // Handle not provided page
  ]},
  { path: "/signup", element: <SignUp /> },
  { path: "/login", element: <Login /> },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)

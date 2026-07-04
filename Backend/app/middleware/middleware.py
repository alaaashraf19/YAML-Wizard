from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:8001",
            "https://sprain-reiterate-cape.ngrok-free.dev",
            "https://gauging-scandal-railway.ngrok-free.dev",
            "https://can-cathedral-dennis-regime.trycloudflare.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
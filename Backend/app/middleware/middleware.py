from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "https://sprain-reiterate-cape.ngrok-free.dev"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
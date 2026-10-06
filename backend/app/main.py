from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models.quiz_registration import QuizRegistration

from app.api.quizzes import router as quizzes_router
from app.api.devices import router as devices_router
from app.api.questions import router as questions_router
from app.api.responses import router as responses_router

from app.api.analytics import router as analytics_router
from app.api.monitoring import router as monitoring_router


app = FastAPI(
    title="PulseNet Backend",
    description="Backend API for PulseNet Smart Wireless Quiz System",
    version="1.0.0",
)

# The teacher tablet loads the dashboard from the Pi over
# Wi-Fi (different origin than the API in some setups).

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices_router)
app.include_router(quizzes_router)
app.include_router(questions_router)
app.include_router(responses_router)
app.include_router(analytics_router)
app.include_router(monitoring_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


# ------------------------------------------------------------
# Teacher web dashboard (static HTML/CSS/JS).
#
# Served at http://<pi-ip>:8000/ so the tablet only needs
# one URL. API routes above take precedence over the mount.
# ------------------------------------------------------------

WEB_DIR = (
    Path(__file__).resolve().parent.parent
    / "web"
)

if WEB_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(WEB_DIR), html=True),
        name="web",
    )

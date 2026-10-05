from fastapi import FastAPI

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

app.include_router(devices_router)
app.include_router(quizzes_router)
app.include_router(questions_router)
app.include_router(responses_router)
app.include_router(analytics_router)
app.include_router(monitoring_router)


@app.get("/")
def root():
    return {
        "message": "PulseNet Backend is running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }

from app.database import Base, engine
from app.models.student import Student
from app.models.device import Device
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.response import Response

print("Creating database...")

Base.metadata.create_all(bind=engine)

print("Database created successfully.")

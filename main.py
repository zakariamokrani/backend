# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Course API")

# Allow CORS from your Flutter app (adjust * to your app domain if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Data Models ----------
class CourseItem(BaseModel):
    id: str
    title: str
    module: Optional[str] = None
    speciality: Optional[str] = None
    year: Optional[str] = None

# --------- Sample Data ----------
courses_db = [
    {"id": "1", "title": "Mathematics 101", "module": "Math", "speciality": "Science", "year": "2026"},
    {"id": "2", "title": "Physics Basics", "module": "Physics", "speciality": "Science", "year": "2026"},
    {"id": "3", "title": "Introduction to Programming", "module": "Computer Science", "speciality": "IT", "year": "2026"},
    {"id": "4", "title": "Chemistry 101", "module": "Chemistry", "speciality": "Science", "year": "2026"},
]

# --------- API Endpoints ----------
@app.get("/files/", response_model=List[CourseItem])
async def get_files():
    """
    Return all course items (simulate files)
    """
    return courses_db

@app.get("/files/{folder_id}", response_model=List[CourseItem])
async def get_folder(folder_id: str):
    """
    Return files filtered by module (simulate folder)
    """
    return [c for c in courses_db if c.get("module") == folder_id]

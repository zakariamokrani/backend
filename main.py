# backend/main.py
from fastapi import FastAPI, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uuid
from datetime import datetime
import os
import logging
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import time

# --------- Logging Setup ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting Course Management API...")
logger.info("=" * 50)

# --------- FastAPI App ----------
app = FastAPI(
    title="Course Management API",
    description="API for managing courses, specialities, years, modules and files",
    version="1.0.0"
)

# --------- CORS Middleware ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Database Setup with Retry Logic ----------
logger.info("Setting up database connection...")

# Get database URL from Railway environment
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Mask password for logging
    masked_url = DATABASE_URL
    if '@' in DATABASE_URL:
        parts = DATABASE_URL.split('@')
        credentials = parts[0].split(':')
        if len(credentials) > 2:
            masked_url = f"{credentials[0]}:********@{parts[1]}"
    logger.info(f"DATABASE_URL found: {masked_url}")
    
    # Fix for Postgres URL format
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info("Fixed postgres:// to postgresql:// URL format")
else:
    logger.warning("No DATABASE_URL found, using SQLite fallback")
    DATABASE_URL = "sqlite:///./test.db"

# Create engine with connection pooling for better reliability
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL debugging
)

# Test database connection with retries
max_retries = 5
retry_count = 0
db_connected = False

while retry_count < max_retries and not db_connected:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful!")
            db_connected = True
    except Exception as e:
        retry_count += 1
        logger.error(f"❌ Database connection attempt {retry_count} failed: {e}")
        if retry_count < max_retries:
            logger.info(f"Retrying in 5 seconds...")
            time.sleep(5)
        else:
            logger.error("⚠️ Max retries reached. Continuing without database connection.")
            logger.error("The app will start but database operations will fail until connection is restored.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --------- Database Models ----------
class SpecialityDB(Base):
    __tablename__ = "specialities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    color = Column(String, nullable=False)

class YearDB(Base):
    __tablename__ = "years"
    
    id = Column(Integer, primary_key=True, index=True)
    specialityId = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

class ModuleDB(Base):
    __tablename__ = "modules"
    
    id = Column(Integer, primary_key=True, index=True)
    yearId = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)

class FileDB(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    moduleId = Column(Integer, nullable=False)
    filename = Column(String, nullable=False)
    title = Column(String, nullable=False)
    fileUrl = Column(String, nullable=False)
    iconName = Column(String, nullable=True)
    colorValue = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.now)
    grouped = Column(String, nullable=False, default="files")

# Create tables
try:
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables created successfully!")
except Exception as e:
    logger.error(f"❌ Failed to create tables: {e}")

# --------- Dependency to get DB session ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
    finally:
        db.close()

# --------- Helper Functions ----------
def get_next_id(db, model):
    """Get next ID for a model"""
    try:
        result = db.query(model).order_by(model.id.desc()).first()
        if result:
            return result.id + 1
        return 1
    except Exception as e:
        logger.error(f"Error getting next ID: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# --------- Speciality Endpoints ----------
@app.post("/specialities", status_code=201)
async def create_speciality(
    name: str = Form(..., description="Name of the speciality"),
    icon: str = Form(..., description="URL of the icon image"),
    color: str = Form(..., description="Color code in hex format"),
    db: Session = Depends(get_db)
):
    """Create a new speciality"""
    try:
        new_id = get_next_id(db, SpecialityDB)
        new_speciality = SpecialityDB(
            id=new_id,
            name=name,
            icon=icon,
            color=color
        )
        db.add(new_speciality)
        db.commit()
        db.refresh(new_speciality)
        logger.info(f"Created speciality: {name} (ID: {new_id})")
        return {
            "id": new_speciality.id,
            "name": new_speciality.name,
            "icon": new_speciality.icon,
            "color": new_speciality.color
        }
    except Exception as e:
        logger.error(f"Error creating speciality: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/specialities", response_model=List[dict])
async def get_specialities(db: Session = Depends(get_db)):
    """Get all specialities"""
    try:
        specialities = db.query(SpecialityDB).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "icon": s.icon,
                "color": s.color
            }
            for s in specialities
        ]
    except Exception as e:
        logger.error(f"Error fetching specialities: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/specialities/{speciality_id}")
async def get_speciality(speciality_id: int, db: Session = Depends(get_db)):
    """Get a specific speciality by ID"""
    try:
        speciality = db.query(SpecialityDB).filter(SpecialityDB.id == speciality_id).first()
        if not speciality:
            raise HTTPException(status_code=404, detail="Speciality not found")
        return {
            "id": speciality.id,
            "name": speciality.name,
            "icon": speciality.icon,
            "color": speciality.color
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching speciality {speciality_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/specialities/{speciality_id}")
async def update_speciality(
    speciality_id: int,
    name: str = Form(...),
    icon: str = Form(...),
    color: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update an existing speciality"""
    try:
        speciality = db.query(SpecialityDB).filter(SpecialityDB.id == speciality_id).first()
        if not speciality:
            raise HTTPException(status_code=404, detail="Speciality not found")
        
        speciality.name = name
        speciality.icon = icon
        speciality.color = color
        db.commit()
        db.refresh(speciality)
        logger.info(f"Updated speciality: {name} (ID: {speciality_id})")
        
        return {
            "id": speciality.id,
            "name": speciality.name,
            "icon": speciality.icon,
            "color": speciality.color
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating speciality {speciality_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/specialities/{speciality_id}")
async def delete_speciality(speciality_id: int, db: Session = Depends(get_db)):
    """Delete a speciality"""
    try:
        speciality = db.query(SpecialityDB).filter(SpecialityDB.id == speciality_id).first()
        if not speciality:
            raise HTTPException(status_code=404, detail="Speciality not found")
        
        # Get all years for this speciality
        years = db.query(YearDB).filter(YearDB.specialityId == speciality_id).all()
        
        # For each year, get modules and delete their files
        for year in years:
            modules = db.query(ModuleDB).filter(ModuleDB.yearId == year.id).all()
            for module in modules:
                db.query(FileDB).filter(FileDB.moduleId == module.id).delete()
            db.query(ModuleDB).filter(ModuleDB.yearId == year.id).delete()
        
        # Delete years and speciality
        db.query(YearDB).filter(YearDB.specialityId == speciality_id).delete()
        db.delete(speciality)
        db.commit()
        logger.info(f"Deleted speciality ID: {speciality_id}")
        
        return {"message": "Speciality and all related data deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting speciality {speciality_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --------- Year Endpoints ----------
@app.post("/years", status_code=201)
async def create_year(
    specialityId: int = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new year"""
    try:
        # Verify speciality exists
        speciality = db.query(SpecialityDB).filter(SpecialityDB.id == specialityId).first()
        if not speciality:
            raise HTTPException(status_code=404, detail=f"Speciality with id {specialityId} not found")
        
        new_id = get_next_id(db, YearDB)
        new_year = YearDB(
            id=new_id,
            specialityId=specialityId,
            name=name
        )
        db.add(new_year)
        db.commit()
        db.refresh(new_year)
        logger.info(f"Created year: {name} for speciality {specialityId} (ID: {new_id})")
        return {
            "id": new_year.id,
            "specialityId": new_year.specialityId,
            "name": new_year.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating year: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/years", response_model=List[dict])
async def get_all_years(db: Session = Depends(get_db)):
    """Get all years across all specialities"""
    try:
        years = db.query(YearDB).all()
        return [
            {
                "id": y.id,
                "specialityId": y.specialityId,
                "name": y.name
            }
            for y in years
        ]
    except Exception as e:
        logger.error(f"Error fetching years: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/specialities/{speciality_id}/years", response_model=List[dict])
async def get_years_by_speciality(speciality_id: int, db: Session = Depends(get_db)):
    """Get all years for a specific speciality"""
    try:
        years = db.query(YearDB).filter(YearDB.specialityId == speciality_id).all()
        return [
            {
                "id": y.id,
                "specialityId": y.specialityId,
                "name": y.name
            }
            for y in years
        ]
    except Exception as e:
        logger.error(f"Error fetching years for speciality {speciality_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/years/{year_id}")
async def get_year(year_id: int, db: Session = Depends(get_db)):
    """Get a specific year by ID"""
    try:
        year = db.query(YearDB).filter(YearDB.id == year_id).first()
        if not year:
            raise HTTPException(status_code=404, detail="Year not found")
        return {
            "id": year.id,
            "specialityId": year.specialityId,
            "name": year.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching year {year_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/years/{year_id}")
async def update_year(
    year_id: int,
    specialityId: int = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update an existing year"""
    try:
        year = db.query(YearDB).filter(YearDB.id == year_id).first()
        if not year:
            raise HTTPException(status_code=404, detail="Year not found")
        
        # Verify speciality exists
        speciality = db.query(SpecialityDB).filter(SpecialityDB.id == specialityId).first()
        if not speciality:
            raise HTTPException(status_code=404, detail=f"Speciality with id {specialityId} not found")
        
        year.specialityId = specialityId
        year.name = name
        db.commit()
        db.refresh(year)
        logger.info(f"Updated year ID: {year_id}")
        
        return {
            "id": year.id,
            "specialityId": year.specialityId,
            "name": year.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating year {year_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/years/{year_id}")
async def delete_year(year_id: int, db: Session = Depends(get_db)):
    """Delete a year"""
    try:
        year = db.query(YearDB).filter(YearDB.id == year_id).first()
        if not year:
            raise HTTPException(status_code=404, detail="Year not found")
        
        # Get modules for this year
        modules = db.query(ModuleDB).filter(ModuleDB.yearId == year_id).all()
        
        # Delete files for each module, then delete modules
        for module in modules:
            db.query(FileDB).filter(FileDB.moduleId == module.id).delete()
        db.query(ModuleDB).filter(ModuleDB.yearId == year_id).delete()
        
        # Delete year
        db.delete(year)
        db.commit()
        logger.info(f"Deleted year ID: {year_id}")
        
        return {"message": "Year and all related modules/files deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting year {year_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --------- Module Endpoints ----------
@app.post("/modules", status_code=201)
async def create_module(
    yearId: int = Form(...),
    name: str = Form(...),
    icon: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new module"""
    try:
        # Verify year exists
        year = db.query(YearDB).filter(YearDB.id == yearId).first()
        if not year:
            raise HTTPException(status_code=404, detail=f"Year with id {yearId} not found")
        
        new_id = get_next_id(db, ModuleDB)
        new_module = ModuleDB(
            id=new_id,
            yearId=yearId,
            name=name,
            icon=icon
        )
        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        logger.info(f"Created module: {name} for year {yearId} (ID: {new_id})")
        return {
            "id": new_module.id,
            "yearId": new_module.yearId,
            "name": new_module.name,
            "icon": new_module.icon
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating module: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/modules", response_model=List[dict])
async def get_all_modules(db: Session = Depends(get_db)):
    """Get all modules across all years"""
    try:
        modules = db.query(ModuleDB).all()
        return [
            {
                "id": m.id,
                "yearId": m.yearId,
                "name": m.name,
                "icon": m.icon
            }
            for m in modules
        ]
    except Exception as e:
        logger.error(f"Error fetching modules: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/years/{year_id}/modules", response_model=List[dict])
async def get_modules_by_year(year_id: int, db: Session = Depends(get_db)):
    """Get all modules for a specific year"""
    try:
        modules = db.query(ModuleDB).filter(ModuleDB.yearId == year_id).all()
        return [
            {
                "id": m.id,
                "yearId": m.yearId,
                "name": m.name,
                "icon": m.icon
            }
            for m in modules
        ]
    except Exception as e:
        logger.error(f"Error fetching modules for year {year_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/modules/{module_id}")
async def get_module(module_id: int, db: Session = Depends(get_db)):
    """Get a specific module by ID"""
    try:
        module = db.query(ModuleDB).filter(ModuleDB.id == module_id).first()
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        return {
            "id": module.id,
            "yearId": module.yearId,
            "name": module.name,
            "icon": module.icon
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching module {module_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/modules/{module_id}")
async def update_module(
    module_id: int,
    yearId: int = Form(...),
    name: str = Form(...),
    icon: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update an existing module"""
    try:
        module = db.query(ModuleDB).filter(ModuleDB.id == module_id).first()
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Verify year exists
        year = db.query(YearDB).filter(YearDB.id == yearId).first()
        if not year:
            raise HTTPException(status_code=404, detail=f"Year with id {yearId} not found")
        
        module.yearId = yearId
        module.name = name
        module.icon = icon
        db.commit()
        db.refresh(module)
        logger.info(f"Updated module ID: {module_id}")
        
        return {
            "id": module.id,
            "yearId": module.yearId,
            "name": module.name,
            "icon": module.icon
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating module {module_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/modules/{module_id}")
async def delete_module(module_id: int, db: Session = Depends(get_db)):
    """Delete a module"""
    try:
        module = db.query(ModuleDB).filter(ModuleDB.id == module_id).first()
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Delete related files
        db.query(FileDB).filter(FileDB.moduleId == module_id).delete()
        db.delete(module)
        db.commit()
        logger.info(f"Deleted module ID: {module_id}")
        
        return {"message": "Module and all related files deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting module {module_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --------- File Endpoints ----------
@app.post("/files", status_code=201)
async def create_file(
    moduleId: int = Form(...),
    filename: str = Form(...),
    title: str = Form(...),
    fileUrl: str = Form(...),
    grouped: str = Form("files"),
    db: Session = Depends(get_db)
):
    """Create a new file (iconName and colorValue removed)"""
    try:
        # Verify module exists
        module = db.query(ModuleDB).filter(ModuleDB.id == moduleId).first()
        if not module:
            raise HTTPException(status_code=404, detail=f"Module with id {moduleId} not found")
        
        new_file = FileDB(
            id=uuid.uuid4(),
            moduleId=moduleId,
            filename=filename,
            title=title,
            fileUrl=fileUrl,
            grouped=grouped,
            createdAt=datetime.now()
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        logger.info(f"Created file: {filename} for module {moduleId}")
        
        return {
            "id": str(new_file.id),
            "moduleId": new_file.moduleId,
            "filename": new_file.filename,
            "title": new_file.title,
            "fileUrl": new_file.fileUrl,
            "grouped": new_file.grouped,
            "createdAt": new_file.createdAt
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/files", response_model=List[dict])
async def get_all_files(db: Session = Depends(get_db)):
    """Get all files across all modules (iconName and colorValue removed)"""
    try:
        files = db.query(FileDB).all()
        return [
            {
                "id": str(f.id),
                "moduleId": f.moduleId,
                "filename": f.filename,
                "title": f.title,
                "fileUrl": f.fileUrl,
                "grouped": f.grouped,
                "createdAt": f.createdAt
            }
            for f in files
        ]
    except Exception as e:
        logger.error(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/modules/{module_id}/files", response_model=List[dict])
async def get_files_by_module(module_id: int, db: Session = Depends(get_db)):
    """Get all files for a specific module (iconName and colorValue removed)"""
    try:
        files = db.query(FileDB).filter(FileDB.moduleId == module_id).all()
        return [
            {
                "id": str(f.id),
                "moduleId": f.moduleId,
                "filename": f.filename,
                "title": f.title,
                "fileUrl": f.fileUrl,
                "grouped": f.grouped,
                "createdAt": f.createdAt
            }
            for f in files
        ]
    except Exception as e:
        logger.error(f"Error fetching files for module {module_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/modules/{module_id}/titles/{title}/files", response_model=List[dict])
async def get_files_by_title(module_id: int, title: str, db: Session = Depends(get_db)):
    """Get files for a specific module and title (iconName and colorValue removed)"""
    try:
        files = db.query(FileDB).filter(
            FileDB.moduleId == module_id,
            FileDB.title == title
        ).all()
        return [
            {
                "id": str(f.id),
                "moduleId": f.moduleId,
                "filename": f.filename,
                "title": f.title,
                "fileUrl": f.fileUrl,
                "grouped": f.grouped,
                "createdAt": f.createdAt
            }
            for f in files
        ]
    except Exception as e:
        logger.error(f"Error fetching files for module {module_id} and title {title}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/files/{file_id}")
async def get_file(file_id: str, db: Session = Depends(get_db)):
    """Get a specific file by ID (iconName and colorValue removed)"""
    try:
        try:
            file_uuid = uuid.UUID(file_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file ID format")
        
        file = db.query(FileDB).filter(FileDB.id == file_uuid).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "id": str(file.id),
            "moduleId": file.moduleId,
            "filename": file.filename,
            "title": file.title,
            "fileUrl": file.fileUrl,
            "grouped": file.grouped,
            "createdAt": file.createdAt
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/files/{file_id}")
async def update_file(
    file_id: str,
    moduleId: int = Form(...),
    filename: str = Form(...),
    title: str = Form(...),
    fileUrl: str = Form(...),
    grouped: str = Form("files"),
    db: Session = Depends(get_db)
):
    """Update an existing file (iconName and colorValue removed)"""
    try:
        try:
            file_uuid = uuid.UUID(file_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file ID format")
        
        file = db.query(FileDB).filter(FileDB.id == file_uuid).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Verify module exists
        module = db.query(ModuleDB).filter(ModuleDB.id == moduleId).first()
        if not module:
            raise HTTPException(status_code=404, detail=f"Module with id {moduleId} not found")
        
        file.moduleId = moduleId
        file.filename = filename
        file.title = title
        file.fileUrl = fileUrl
        file.grouped = grouped
        db.commit()
        db.refresh(file)
        logger.info(f"Updated file ID: {file_id}")
        
        return {
            "id": str(file.id),
            "moduleId": file.moduleId,
            "filename": file.filename,
            "title": file.title,
            "fileUrl": file.fileUrl,
            "grouped": file.grouped,
            "createdAt": file.createdAt
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file {file_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """Delete a file"""
    try:
        try:
            file_uuid = uuid.UUID(file_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file ID format")
        
        file = db.query(FileDB).filter(FileDB.id == file_uuid).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        db.delete(file)
        db.commit()
        logger.info(f"Deleted file ID: {file_id}")
        
        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --------- Utility Endpoints ----------
@app.get("/modules/{module_id}/titles")
async def get_unique_titles(module_id: int, db: Session = Depends(get_db)):
    """Get unique titles for a specific module"""
    try:
        titles = db.query(FileDB.title).filter(FileDB.moduleId == module_id).distinct().all()
        return [title[0] for title in titles]
    except Exception as e:
        logger.error(f"Error fetching titles for module {module_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check for Railway - always returns 200"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Course Management API",
        "database_url_configured": "Yes" if os.getenv("DATABASE_URL") else "No"
    }

@app.get("/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Detailed health check with database status"""
    try:
        db.execute(text("SELECT 1")).first()
        db_status = "connected"
        overall_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "service": "Course Management API"
    }

@app.get("/")
async def root():
    return {
        "message": "Course Management API is running with PostgreSQL", 
        "status": "ok",
        "documentation": "/docs",
        "health_check": {
            "basic": "/health",
            "with_db": "/health/db"
        },
        "environment": {
            "database_configured": "Yes" if os.getenv("DATABASE_URL") else "No",
            "python_version": sys.version.split()[0]
        },
        "endpoints": {
            "specialities": {
                "get_all": "GET /specialities",
                "get_one": "GET /specialities/{id}",
                "create": "POST /specialities",
                "update": "PUT /specialities/{id}",
                "delete": "DELETE /specialities/{id}"
            },
            "years": {
                "get_all": "GET /years",
                "get_by_speciality": "GET /specialities/{speciality_id}/years",
                "get_one": "GET /years/{id}",
                "create": "POST /years",
                "update": "PUT /years/{id}",
                "delete": "DELETE /years/{id}"
            },
            "modules": {
                "get_all": "GET /modules",
                "get_by_year": "GET /years/{year_id}/modules",
                "get_one": "GET /modules/{id}",
                "create": "POST /modules",
                "update": "PUT /modules/{id}",
                "delete": "DELETE /modules/{id}"
            },
            "files": {
                "get_all": "GET /files",
                "get_by_module": "GET /modules/{module_id}/files",
                "get_by_title": "GET /modules/{module_id}/titles/{title}/files",
                "get_one": "GET /files/{id}",
                "create": "POST /files",
                "update": "PUT /files/{id}",
                "delete": "DELETE /files/{id}"
            }
        }
    }
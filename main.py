# backend/main.py
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI(
    title="Course Management API",
    description="API for managing courses, specialities, years, modules and files",
    version="1.0.0"
)

# Allow CORS from your Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- In-Memory Databases ----------
specialities_db = []
years_db = []
modules_db = []
files_db = []

# --------- Helper Functions ----------
def get_next_id(db_list):
    if not db_list:
        return 1
    return max(item["id"] for item in db_list) + 1

# --------- Speciality Endpoints ----------
@app.post(
    "/specialities", 
    status_code=201,
    summary="Create a new speciality",
    description="Create a speciality by providing name, icon URL, and color"
)
async def create_speciality(
    name: str = Form(..., description="Name of the speciality"),
    icon: str = Form(..., description="URL of the icon image"),
    color: str = Form(..., description="Color code in hex format")
):
    """Create a new speciality - you provide name, icon, color - server generates ID"""
    new_speciality = {
        "id": get_next_id(specialities_db),
        "name": name,
        "icon": icon,
        "color": color
    }
    specialities_db.append(new_speciality)
    return new_speciality

@app.get("/specialities", response_model=List[dict])
async def get_specialities():
    """Get all specialities"""
    return specialities_db

@app.get("/specialities/{speciality_id}", response_model=dict)
async def get_speciality(speciality_id: int):
    """Get a specific speciality by ID"""
    speciality = next((s for s in specialities_db if s["id"] == speciality_id), None)
    if not speciality:
        raise HTTPException(status_code=404, detail="Speciality not found")
    return speciality

@app.put("/specialities/{speciality_id}")
async def update_speciality(
    speciality_id: int,
    name: str = Form(..., description="Name of the speciality"),
    icon: str = Form(..., description="URL of the icon image"),
    color: str = Form(..., description="Color code in hex format")
):
    """Update an existing speciality"""
    index = next((i for i, s in enumerate(specialities_db) if s["id"] == speciality_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Speciality not found")
    
    updated_speciality = {
        "id": speciality_id,
        "name": name,
        "icon": icon,
        "color": color
    }
    specialities_db[index] = updated_speciality
    return updated_speciality

@app.delete("/specialities/{speciality_id}")
async def delete_speciality(speciality_id: int):
    """Delete a speciality"""
    global specialities_db, years_db, modules_db, files_db
    
    speciality = next((s for s in specialities_db if s["id"] == speciality_id), None)
    if not speciality:
        raise HTTPException(status_code=404, detail="Speciality not found")
    
    # Delete all related data
    years_to_delete = [y for y in years_db if y["specialityId"] == speciality_id]
    for year in years_to_delete:
        modules_to_delete = [m for m in modules_db if m["yearId"] == year["id"]]
        for module in modules_to_delete:
            files_db = [f for f in files_db if f["moduleId"] != module["id"]]
        modules_db = [m for m in modules_db if m["yearId"] != year["id"]]
    years_db = [y for y in years_db if y["specialityId"] != speciality_id]
    specialities_db = [s for s in specialities_db if s["id"] != speciality_id]
    
    return {"message": "Speciality and all related data deleted successfully"}

# --------- Year Endpoints ----------
@app.get("/years", response_model=List[dict])
async def get_all_years():
    """Get all years across all specialities"""
    return years_db

@app.post(
    "/years", 
    status_code=201,
    summary="Create a new year",
    description="Create a year by providing specialityId and name"
)
async def create_year(
    specialityId: int = Form(..., description="ID of the speciality this year belongs to"),
    name: str = Form(..., description="Year name (L1, L2, L3, M1, M2)")
):
    """Create a new year - you provide specialityId and name - server generates ID"""
    speciality = next((s for s in specialities_db if s["id"] == specialityId), None)
    if not speciality:
        raise HTTPException(status_code=404, detail=f"Speciality with id {specialityId} not found")
    
    new_year = {
        "id": get_next_id(years_db),
        "specialityId": specialityId,
        "name": name
    }
    years_db.append(new_year)
    return new_year

@app.get("/specialities/{speciality_id}/years", response_model=List[dict])
async def get_years_by_speciality(speciality_id: int):
    """Get all years for a specific speciality"""
    return [y for y in years_db if y["specialityId"] == speciality_id]

@app.get("/years/{year_id}", response_model=dict)
async def get_year(year_id: int):
    """Get a specific year by ID"""
    year = next((y for y in years_db if y["id"] == year_id), None)
    if not year:
        raise HTTPException(status_code=404, detail="Year not found")
    return year

@app.put("/years/{year_id}")
async def update_year(
    year_id: int,
    specialityId: int = Form(..., description="ID of the speciality this year belongs to"),
    name: str = Form(..., description="Year name (L1, L2, L3, M1, M2)")
):
    """Update an existing year"""
    index = next((i for i, y in enumerate(years_db) if y["id"] == year_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Year not found")
    
    speciality = next((s for s in specialities_db if s["id"] == specialityId), None)
    if not speciality:
        raise HTTPException(status_code=404, detail=f"Speciality with id {specialityId} not found")
    
    updated_year = {
        "id": year_id,
        "specialityId": specialityId,
        "name": name
    }
    years_db[index] = updated_year
    return updated_year

@app.delete("/years/{year_id}")
async def delete_year(year_id: int):
    """Delete a year"""
    global years_db, modules_db, files_db
    
    year = next((y for y in years_db if y["id"] == year_id), None)
    if not year:
        raise HTTPException(status_code=404, detail="Year not found")
    
    # Delete all related modules and files
    modules_to_delete = [m for m in modules_db if m["yearId"] == year_id]
    for module in modules_to_delete:
        files_db = [f for f in files_db if f["moduleId"] != module["id"]]
    modules_db = [m for m in modules_db if m["yearId"] != year_id]
    years_db = [y for y in years_db if y["id"] != year_id]
    
    return {"message": "Year and all related modules/files deleted successfully"}

# --------- Module Endpoints ----------
@app.get("/modules", response_model=List[dict])
async def get_all_modules():
    """Get all modules across all years"""
    return modules_db

@app.post(
    "/modules", 
    status_code=201,
    summary="Create a new module",
    description="Create a module by providing yearId, name, and icon URL"
)
async def create_module(
    yearId: int = Form(..., description="ID of the year this module belongs to"),
    name: str = Form(..., description="Name of the module"),
    icon: str = Form(..., description="URL of the module icon")
):
    """Create a new module - you provide yearId, name, icon - server generates ID"""
    year = next((y for y in years_db if y["id"] == yearId), None)
    if not year:
        raise HTTPException(status_code=404, detail=f"Year with id {yearId} not found")
    
    new_module = {
        "id": get_next_id(modules_db),
        "yearId": yearId,
        "name": name,
        "icon": icon
    }
    modules_db.append(new_module)
    return new_module

@app.get("/years/{year_id}/modules", response_model=List[dict])
async def get_modules_by_year(year_id: int):
    """Get all modules for a specific year"""
    return [m for m in modules_db if m["yearId"] == year_id]

@app.get("/modules/{module_id}", response_model=dict)
async def get_module(module_id: int):
    """Get a specific module by ID"""
    module = next((m for m in modules_db if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module

@app.put("/modules/{module_id}")
async def update_module(
    module_id: int,
    yearId: int = Form(..., description="ID of the year this module belongs to"),
    name: str = Form(..., description="Name of the module"),
    icon: str = Form(..., description="URL of the module icon")
):
    """Update an existing module"""
    index = next((i for i, m in enumerate(modules_db) if m["id"] == module_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Module not found")
    
    year = next((y for y in years_db if y["id"] == yearId), None)
    if not year:
        raise HTTPException(status_code=404, detail=f"Year with id {yearId} not found")
    
    updated_module = {
        "id": module_id,
        "yearId": yearId,
        "name": name,
        "icon": icon
    }
    modules_db[index] = updated_module
    return updated_module

@app.delete("/modules/{module_id}")
async def delete_module(module_id: int):
    """Delete a module"""
    global modules_db, files_db
    
    module = next((m for m in modules_db if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Delete all related files
    files_db = [f for f in files_db if f["moduleId"] != module_id]
    modules_db = [m for m in modules_db if m["id"] != module_id]
    
    return {"message": "Module and all related files deleted successfully"}

# --------- File Endpoints ----------
@app.get("/files", response_model=List[dict])
async def get_all_files():
    """Get all files across all modules with grouped field added"""
    files_response = []
    for file in files_db:
        file_copy = file.copy()
        file_copy["grouped"] = "files"
        files_response.append(file_copy)
    return files_response

@app.post(
    "/files", 
    status_code=201,
    summary="Create a new file",
    description="Create a file by providing moduleId, filename, title, and fileUrl"
)
async def create_file(
    moduleId: int = Form(..., description="ID of the module this file belongs to"),
    filename: str = Form(..., description="Name of the file"),
    title: str = Form(..., description="Type of content (Course, TD, or TP)"),
    Grouped: str = Form("files", description="Group name for the file"),
    fileUrl: str = Form(..., description="URL where the file is stored")
):
    """Create a new file - you provide moduleId, filename, title, fileUrl - server generates ID"""
    module = next((m for m in modules_db if m["id"] == moduleId), None)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module with id {moduleId} not found")
    
    new_file = {
        "id": str(uuid.uuid4()),
        "moduleId": moduleId,
        "filename": filename,
        "title": title,
        "grouped": grouped,
        "fileUrl": fileUrl,
        "createdAt": datetime.now(),
    }
    files_db.append(new_file)
    return new_file

@app.get("/modules/{module_id}/files", response_model=List[dict])
async def get_files_by_module(module_id: int):
    """Get all files for a specific module"""
    return [f for f in files_db if f["moduleId"] == module_id]

@app.get("/modules/{module_id}/titles/{title}/files", response_model=List[dict])
async def get_files_by_title(module_id: int, title: str):
    """Get files for a specific module and title"""
    return [f for f in files_db if f["moduleId"] == module_id and f["title"] == title]

@app.get("/files/{file_id}", response_model=dict)
async def get_file(file_id: str):
    """Get a specific file by ID"""
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.put("/files/{file_id}")
async def update_file(
    file_id: str,
    moduleId: int = Form(..., description="ID of the module this file belongs to"),
    filename: str = Form(..., description="Name of the file"),
    title: str = Form(..., description="Type of content (Course, TD, or TP)"),
    grouped: str = Form("files", description="Group name for the file"),
    fileUrl: str = Form(..., description="URL where the file is stored")
):
    """Update an existing file"""
    index = next((i for i, f in enumerate(files_db) if f["id"] == file_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    module = next((m for m in modules_db if m["id"] == moduleId), None)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module with id {moduleId} not found")
    
    updated_file = {
        "id": file_id,
        "moduleId": moduleId,
        "filename": filename,
        "title": title,
        "grouped": grouped,
        "fileUrl": fileUrl,
        "createdAt": files_db[index]["createdAt"],
        "grouped": "files"  # Added grouped field to PUT response
    }
    files_db[index] = updated_file
    return updated_file

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    global files_db
    
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    files_db = [f for f in files_db if f["id"] != file_id]
    return {"message": "File deleted successfully"}

# --------- Utility Endpoints ----------
@app.get("/modules/{module_id}/titles")
async def get_unique_titles(module_id: int):
    """Get unique titles for a specific module"""
    titles = set()
    for file in files_db:
        if file["moduleId"] == module_id and file.get("title"):
            titles.add(file["title"])
    return sorted(list(titles))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/")
async def root():
    return {
        "message": "Course Management API is running", 
        "status": "ok",
        "documentation": "/docs",
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

# Run with: uvicorn main:app --reload

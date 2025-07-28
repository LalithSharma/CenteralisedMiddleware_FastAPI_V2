from datetime import datetime
import os
from fastapi import APIRouter, HTTPException
from pathlib import Path
from fastapi.responses import JSONResponse, PlainTextResponse
from auth.schemas import LogFilesResponse 

router = APIRouter()

# BASE_LOG_DIR = (Path(__file__).parent / "static").resolve()
# ALLOWED_DIRS = {"applogs", "middlewarelogs"}
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"

if IS_PRODUCTION:
    BASE_LOG_DIR = Path("/tmp/logs").resolve()
    ALLOWED_DIRS = {""}
else:
    BASE_LOG_DIR = (Path(__file__).parent / "static").resolve()
    ALLOWED_DIRS = {"applogs", "middlewarelogs"}

@router.get("/{log_type}/{filename}", response_class=PlainTextResponse)
async def read_log_file(log_type: str, filename: str):
    if IS_PRODUCTION:
        if log_type != "":
            raise HTTPException(status_code=400, detail="Invalid log type")
        log_path = (BASE_LOG_DIR / filename).resolve()
        
    else:
        if log_type not in ALLOWED_DIRS:
            raise HTTPException(status_code=400, detail="Invalid log type")

        if any(char in filename for char in ["/", "\\", ".."]):
            raise HTTPException(status_code=400, detail="Invalid filename")
        log_path = (BASE_LOG_DIR / log_type / filename).resolve()

    if not str(log_path).startswith(str(BASE_LOG_DIR)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        return log_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/{log_type}", response_model=LogFilesResponse)
async def list_log_files(log_type: str):
    if IS_PRODUCTION:
        if log_type != "":
            raise HTTPException(status_code=400, detail="Invalid log type")
        log_folder = BASE_LOG_DIR
        
    else:
        if log_type not in ALLOWED_DIRS:
            raise HTTPException(status_code=400, detail="Invalid log type")
        log_folder = (BASE_LOG_DIR / log_type).resolve()
        print("getting log folder location", log_folder)

    if not str(log_folder).startswith(str(BASE_LOG_DIR)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not log_folder.exists() or not log_folder.is_dir():
        raise HTTPException(status_code=404, detail="Log folder not found")

    log_files = []
    for f in log_folder.glob("*.log"):
        if f.is_file():
            stat = f.stat()
            log_files.append({
                "filename": f.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime)
            })

    log_files.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "message": "Logs retrieved successfully",
        "result": True,
        "data": log_files
    }

@router.delete("/{log_type}/{filename}")
async def delete_log_file(log_type: str, filename: str):
    if log_type not in ALLOWED_DIRS:
        raise HTTPException(status_code=400, detail="Invalid log type")

    if any(char in filename for char in ["/", "\\", ".."]):
        raise HTTPException(status_code=400, detail="Invalid filename")

    log_path = (BASE_LOG_DIR / log_type / filename).resolve()

    if not str(log_path).startswith(str(BASE_LOG_DIR)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")
    print("deleteing files from api")
    try:
        log_path.unlink()  # or os.remove(log_path)
        return JSONResponse(
            status_code=200,
            content={"result": True, "message": "Log file deleted successfully"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
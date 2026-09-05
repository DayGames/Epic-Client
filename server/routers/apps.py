"""App catalog: list, upload, download."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import auth
from config import settings
from database import get_db

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=list[schemas.AppOut])
def list_apps(db: Session = Depends(get_db)):
    """Public: anyone can browse the catalog."""
    return db.query(models.App).order_by(models.App.uploaded_at.desc()).all()


@router.get("/{app_id}", response_model=schemas.AppOut)
def get_app(app_id: int, db: Session = Depends(get_db)):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.post("", response_model=schemas.AppOut)
def upload_app(
    name: str = Form(...),
    description: str = Form(""),
    version: str = Form("1.0.0"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Logged-in users upload an installer. Stored on disk; DB keeps the metadata."""
    # Give every upload a unique on-disk name so files never collide.
    suffix = Path(file.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = settings.files_dir / stored_name

    size = 0
    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):  # stream 1 MB at a time
            out.write(chunk)
            size += len(chunk)

    app = models.App(
        name=name,
        description=description,
        version=version,
        filename=stored_name,
        size_bytes=size,
        owner_id=current_user.id,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}/download")
def download_app(app_id: int, db: Session = Depends(get_db)):
    """Public download of an app's installer file."""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    path = settings.files_dir / app.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on server")

    download_name = f"{app.name}-{app.version}{path.suffix}"
    return FileResponse(path, filename=download_name, media_type="application/octet-stream")

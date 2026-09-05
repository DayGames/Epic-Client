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


def _save_upload(upload: UploadFile) -> tuple[str, int]:
    """Stream an uploaded file to disk under a unique name. Returns (stored_name, size)."""
    suffix = Path(upload.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = settings.files_dir / stored_name
    size = 0
    with dest.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):  # 1 MB at a time
            out.write(chunk)
            size += len(chunk)
    return stored_name, size


def _add_media(db: Session, app_id: int, uploads: list[UploadFile] | None, kind: str):
    """Save a list of media uploads (images or videos) attached to an app."""
    for up in uploads or []:
        if not up or not up.filename:
            continue
        stored, _ = _save_upload(up)
        db.add(models.Media(app_id=app_id, filename=stored, kind=kind))


def _require_owner(app: models.App | None, user: models.User) -> models.App:
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    if app.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can do that")
    return app


@router.post("", response_model=schemas.AppOut)
def upload_app(
    name: str = Form(...),
    description: str = Form(""),
    version: str = Form("1.0.0"),
    file: UploadFile = File(...),
    icon: UploadFile | None = File(None),
    images: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Logged-in users upload a game as a .zip (+ optional icon, screenshots, videos)."""
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="The game file must be a .zip archive")
    stored_name, size = _save_upload(file)

    icon_name = None
    if icon is not None and icon.filename:
        icon_name, _ = _save_upload(icon)

    app = models.App(
        name=name,
        description=description,
        version=version,
        filename=stored_name,
        icon_filename=icon_name,
        size_bytes=size,
        owner_id=current_user.id,
    )
    db.add(app)
    db.flush()  # assigns app.id so media can reference it

    _add_media(db, app.id, images, "image")
    _add_media(db, app.id, videos, "video")

    db.commit()
    db.refresh(app)
    return app


@router.patch("/{app_id}", response_model=schemas.AppOut)
def edit_app(
    app_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    version: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Owner-only: edit an app's name / description / version."""
    app = _require_owner(db.query(models.App).filter(models.App.id == app_id).first(), current_user)
    if name is not None and name.strip():
        app.name = name.strip()
    if description is not None:
        app.description = description
    if version is not None and version.strip():
        app.version = version.strip()
    db.commit()
    db.refresh(app)
    return app


@router.post("/{app_id}/media", response_model=schemas.AppOut)
def add_media(
    app_id: int,
    images: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Owner-only: attach more screenshots / videos to an app."""
    app = _require_owner(db.query(models.App).filter(models.App.id == app_id).first(), current_user)
    _add_media(db, app.id, images, "image")
    _add_media(db, app.id, videos, "video")
    db.commit()
    db.refresh(app)
    return app


@router.post("/{app_id}/dlc", response_model=schemas.AppOut)
def add_dlc(
    app_id: int,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Owner-only: add DLC (another .zip) to an app."""
    app = _require_owner(db.query(models.App).filter(models.App.id == app_id).first(), current_user)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="DLC must be a .zip archive")
    stored, size = _save_upload(file)
    db.add(models.Dlc(app_id=app.id, name=name, filename=stored, size_bytes=size))
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}/media/{media_id}")
def get_media(app_id: int, media_id: int, db: Session = Depends(get_db)):
    """Serve a screenshot or video file."""
    m = db.query(models.Media).filter(
        models.Media.id == media_id, models.Media.app_id == app_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Media not found")
    path = settings.files_dir / m.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing on server")
    return FileResponse(path)


@router.get("/{app_id}/dlc/{dlc_id}/download")
def download_dlc(app_id: int, dlc_id: int, db: Session = Depends(get_db)):
    """Download a DLC .zip."""
    d = db.query(models.Dlc).filter(
        models.Dlc.id == dlc_id, models.Dlc.app_id == app_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="DLC not found")
    path = settings.files_dir / d.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="DLC file missing on server")
    return FileResponse(path, filename=f"{d.name}.zip", media_type="application/octet-stream")


@router.get("/{app_id}/icon")
def get_icon(app_id: int, db: Session = Depends(get_db)):
    """Serve an app's icon image, or 404 if it has none."""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app or not app.icon_filename:
        raise HTTPException(status_code=404, detail="No icon")
    path = settings.files_dir / app.icon_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Icon missing on server")
    return FileResponse(path)


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

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..ml.cv import process_upload
from ..security import ROLE_ADMIN, ROLE_OPS

router = APIRouter(prefix="/computer-vision", tags=["computer-vision"])

CV_ROLES = (ROLE_ADMIN, ROLE_OPS)

MAX_UPLOAD_MB = 30


@router.post("/analyze")
async def analyze_upload(
    file: UploadFile,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*CV_ROLES))] = None,
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Only video uploads are accepted")

    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Video exceeds {MAX_UPLOAD_MB}MB limit")

    suffix = f".{file.filename.rsplit('.', 1)[-1]}" if "." in (file.filename or "") else ".mp4"
    try:
        result = process_upload(data, suffix)
    except Exception as exc:  # noqa: BLE001 - surface parser errors to the caller
        raise HTTPException(status_code=422, detail=f"Could not process video: {exc}") from exc

    log_action(
        db,
        current.user.id,
        current.site_id,
        "cv_analyze",
        "video",
        None,
        f"{file.filename} → aggregate only",
    )
    db.commit()

    return {
        "filename": file.filename,
        **result,
        "tag": "HOG person detector — aggregate metrics only, frames never stored",
        "privacy": "no_facial_recognition",
    }

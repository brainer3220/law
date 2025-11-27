import os
import shutil
import tempfile
import uuid
from typing import Any

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form
from app.worker import transcribe_audio_file
from app import db

router = APIRouter(prefix="/transcribe", tags=["transcribe"])

def process_transcription(job_id: str, audio_path: str):
    """
    Background task wrapper to run transcription and update job status.
    """
    try:
        db.update_job_status(job_id, "PROCESSING")
        result = transcribe_audio_file(audio_path)
        db.update_job_result(job_id, result)
    except Exception as e:
        db.update_job_error(job_id, str(e))
    finally:
        # Clean up the temp file
        if os.path.exists(audio_path):
            os.remove(audio_path)

@router.post("/")
async def create_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    email: str = Form(...),
) -> dict[str, str]:
    """
    Upload an audio file and start a background transcription task.
    """
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(file.filename or "")[1])
    try:
        with os.fdopen(fd, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    job_id = str(uuid.uuid4())
    db.create_job(job_id, email)

    background_tasks.add_task(process_transcription, job_id, path)
    
    return {"task_id": job_id}

@router.get("/{task_id}")
async def get_transcription_status(task_id: str) -> dict[str, Any]:
    """
    Check the status of a transcription task.
    """
    job = db.get_job(task_id)
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "task_id": task_id,
        "status": job["status"],
    }

    if job["status"] == "SUCCESS":
        response["result"] = job["result"]
    elif job["status"] == "FAILURE":
        response["error"] = job.get("error")
    
    return response

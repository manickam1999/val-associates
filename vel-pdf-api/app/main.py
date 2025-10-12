"""
FastAPI Backend for Vel PDF Converter
Handles PDF/ZIP uploads, processing, and Excel generation with WebSocket progress.
"""

import os
import uuid
import shutil
import time
from pathlib import Path
from typing import List
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from .batch_processor import BatchProcessor
from .models import UploadResponse, ProgressMessage

load_dotenv()

app = FastAPI(
    title="Vel PDF API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
if cors_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except:
                self.disconnect(session_id)

manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "vel-pdf-api"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload PDF or ZIP files for processing."""
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = []

    for file in files:
        file_path = session_dir / file.filename

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Handle ZIP files
        if file.filename.lower().endswith('.zip'):
            processor = BatchProcessor()
            extracted_pdfs = await processor.extract_zip(str(file_path), str(session_dir / "extracted"))
            pdf_files.extend(extracted_pdfs)
        elif file.filename.lower().endswith('.pdf'):
            pdf_files.append(str(file_path))

    return UploadResponse(
        session_id=session_id,
        message="Files uploaded successfully",
        total_files=len(pdf_files)
    )


@app.websocket("/ws/progress/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str, modes: str = "everything"):
    """WebSocket endpoint for real-time progress updates."""
    await manager.connect(session_id, websocket)

    try:
        session_dir = UPLOAD_DIR / session_id

        if not session_dir.exists():
            await websocket.send_json({
                "current": 0,
                "total": 0,
                "status": "error",
                "message": "Session not found"
            })
            return

        # Find all PDFs in session directory
        pdf_files = list(session_dir.glob("*.pdf"))
        pdf_files.extend(session_dir.glob("extracted/**/*.pdf"))
        pdf_files = [str(f) for f in pdf_files]

        if not pdf_files:
            await websocket.send_json({
                "current": 0,
                "total": 0,
                "status": "error",
                "message": "No PDF files found"
            })
            return

        # Process PDFs with progress callback
        processor = BatchProcessor()
        start_time = time.time()

        async def progress_callback(current: int, total: int, message: str, item_status: str):
            elapsed = time.time() - start_time
            await manager.send_progress(session_id, {
                "current": current,
                "total": total,
                "status": "processing",
                "message": message,
                "item_status": item_status,
                "elapsed_time": round(elapsed, 2)
            })

        all_data, failed_files = await processor.process_pdfs(pdf_files, progress_callback)

        # Parse modes parameter (comma-separated)
        mode_list = [m.strip() for m in modes.split(',') if m.strip() in ['everything', 'minimal']]
        if not mode_list:
            mode_list = ['everything']

        # Generate Excel files for each mode
        generated_files = []
        for mode in mode_list:
            output_file = OUTPUT_DIR / f"{session_id}_{mode}.xlsx"
            total_records = processor.combine_to_excel(all_data, str(output_file), mode=mode)
            generated_files.append(f"{mode}.xlsx")

        # Send completion message
        elapsed_time = time.time() - start_time
        files_str = ", ".join(generated_files)

        success_count = len(all_data)
        failed_count = len(failed_files)

        if failed_count > 0:
            message = f"Processed {success_count} of {len(pdf_files)} files ({failed_count} failed). Generated {files_str} with {total_records} records"
        else:
            message = f"Completed! Generated {files_str} with {total_records} records"

        await manager.send_progress(session_id, {
            "current": len(pdf_files),
            "total": len(pdf_files),
            "status": "completed",
            "message": message,
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_files": failed_files,
            "elapsed_time": round(elapsed_time, 2)
        })

        # Keep connection open to receive acknowledgment
        await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_progress(session_id, {
            "current": 0,
            "total": 0,
            "status": "error",
            "message": f"Error: {str(e)}"
        })
    finally:
        manager.disconnect(session_id)


@app.get("/api/download/{session_id}")
async def download_excel(session_id: str, mode: str = "everything"):
    """Download generated Excel file."""
    # Validate mode
    if mode not in ['everything', 'minimal']:
        mode = 'everything'

    output_file = OUTPUT_DIR / f"{session_id}_{mode}.xlsx"

    if not output_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(output_file),
        filename=f"str_data_{mode}_{session_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.delete("/api/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session files (optional endpoint)."""
    session_dir = UPLOAD_DIR / session_id

    if session_dir.exists():
        shutil.rmtree(session_dir)

    # Clean up all mode-specific Excel files
    for mode in ['everything', 'minimal']:
        output_file = OUTPUT_DIR / f"{session_id}_{mode}.xlsx"
        if output_file.exists():
            output_file.unlink()

    return {"message": "Session cleaned up successfully"}
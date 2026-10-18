"""
InterviewIQ Main Application Server.
FastAPI with WebSockets for real-time OpenCV computer vision, speech transcription,
authoritative 60-second interview clock, and report generation.
"""
import os
import sys
import json
import asyncio
import logging
from typing import Dict, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    BASE_DIR,
    FRONTEND_DIR,
    STATIC_DIR,
    HAAR_FACE_PATH,
    FACE_LANDMARKER_PATH,
    POSE_LANDMARKER_PATH,
    INTERVIEW_DURATION_SECONDS
)
from backend.interview.session_manager import InterviewSessionManager
from backend.scoring.report_generator import ReportGenerator
from backend.interview.question_bank import CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("InterviewIQ")

app = FastAPI(
    title="InterviewIQ",
    description="Real-Time AI Mock Interviewer with OpenCV Vision and Speech Analysis",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def get_index():
    """Serves the main application landing and dashboard."""
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return FileResponse(str(index_file))

@app.get("/api/health")
async def health_check():
    """System health check and local model diagnostic status."""
    return {
        "status": "healthy",
        "python_version": sys.version,
        "models": {
            "haar_cascade_face": HAAR_FACE_PATH.exists(),
            "mediapipe_face_landmarker": FACE_LANDMARKER_PATH.exists(),
            "mediapipe_pose_landmarker": POSE_LANDMARKER_PATH.exists()
        },
        "interview_duration_seconds": INTERVIEW_DURATION_SECONDS
    }

@app.get("/api/categories")
async def get_categories():
    """Returns available interview question categories."""
    return {"categories": CATEGORIES}

@app.websocket("/ws/interview")
async def websocket_interview_endpoint(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket connection.
    Streams webcam frames, audio transcripts, authoritative countdown ticks,
    adaptive questions, and final reports.
    """
    await websocket.accept()
    logger.info("WebSocket connection established.")

    session_manager: Optional[InterviewSessionManager] = None
    report_generator = ReportGenerator()
    timer_task: Optional[asyncio.Task] = None

    async def authoritative_timer_loop():
        """Asynchronously updates countdown and triggers completion exactly at 60s."""
        try:
            while session_manager and session_manager.state == "IN_PROGRESS":
                await asyncio.sleep(0.5)
                time_rem = session_manager.get_time_remaining()

                # Broadcast timer tick to keep frontend authoritative
                try:
                    await websocket.send_text(json.dumps({
                        "type": "timer_tick",
                        "time_remaining_seconds": time_rem
                    }))
                except Exception:
                    break

                if time_rem <= 0.0:
                    logger.info("Authoritative 60-second timer reached 0. Finalizing session.")
                    session_data = session_manager.complete()
                    final_report = report_generator.generate(
                        session_id=session_data["session_id"],
                        category=session_data["category"],
                        vision_summary=session_data["vision_summary"],
                        speech_summary=session_data["speech_summary"],
                        qna_history=session_data["qna_history"],
                        duration_seconds=session_data["duration_seconds"]
                    )
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "session_completed",
                            "report": final_report
                        }))
                    except Exception as e:
                        logger.error(f"Error sending completion report: {e}")
                    break
        except asyncio.CancelledError:
            pass

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            msg_type = payload.get("type")

            # 1. Start / Initialize Interview
            if msg_type == "start_session":
                category = payload.get("category", "General")
                session_manager = InterviewSessionManager(category=category)
                start_info = session_manager.start()

                # Start the background authoritative timer loop
                if timer_task and not timer_task.done():
                    timer_task.cancel()
                timer_task = asyncio.create_task(authoritative_timer_loop())

                await websocket.send_text(json.dumps({
                    "type": "session_started",
                    "data": start_info
                }))

            # 2. Process Video Frame with OpenCV
            elif msg_type == "video_frame":
                if session_manager and session_manager.state == "IN_PROGRESS":
                    base64_data = payload.get("frame", "")
                    # Process frame in executor to prevent blocking the async loop
                    loop = asyncio.get_running_loop()
                    vision_result = await loop.run_in_executor(
                        None,
                        session_manager.frame_processor.process_base64_frame,
                        base64_data
                    )

                    if vision_result is not None:
                        await websocket.send_text(json.dumps({
                            "type": "vision_telemetry",
                            "data": vision_result
                        }))

            # 3. Speech Transcript Update
            elif msg_type == "transcript_update":
                if session_manager and session_manager.state == "IN_PROGRESS":
                    text = payload.get("text", "")
                    is_final = bool(payload.get("is_final", False))
                    session_manager.update_transcript(text, is_final=is_final)

            # 4. Advance Question (Candidate finished answer or requested next)
            elif msg_type == "advance_question":
                if session_manager and session_manager.state == "IN_PROGRESS":
                    manual_text = payload.get("manual_transcript")
                    advance_info = session_manager.advance_question(manual_transcript=manual_text)
                    await websocket.send_text(json.dumps({
                        "type": "question_advanced",
                        "data": advance_info
                    }))

            # 5. Premature Stop / Cancel requested by user
            elif msg_type == "stop_session":
                if session_manager and session_manager.state == "IN_PROGRESS":
                    session_data = session_manager.complete()
                    final_report = report_generator.generate(
                        session_id=session_data["session_id"],
                        category=session_data["category"],
                        vision_summary=session_data["vision_summary"],
                        speech_summary=session_data["speech_summary"],
                        qna_history=session_data["qna_history"],
                        duration_seconds=INTERVIEW_DURATION_SECONDS - session_manager.get_time_remaining()
                    )
                    await websocket.send_text(json.dumps({
                        "type": "session_completed",
                        "report": final_report
                    }))
                    if timer_task and not timer_task.done():
                        timer_task.cancel()

            # 6. Heartbeat Ping
            elif msg_type == "ping":
                rem = session_manager.get_time_remaining() if session_manager else 0.0
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "time_remaining_seconds": rem
                }))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected gracefully.")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
    finally:
        if timer_task and not timer_task.done():
            timer_task.cancel()
        if session_manager and session_manager.state == "IN_PROGRESS":
            session_manager.state = "TERMINATED"
        logger.info("WebSocket session cleaned up.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

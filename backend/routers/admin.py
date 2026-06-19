from fastapi import APIRouter, BackgroundTasks
import subprocess
import time
import sys
import os
import datetime

router = APIRouter(prefix="/api/admin/sync", tags=["admin"])

# Global state for sync jobs
current_job = {
    "is_running": False,
    "logs": [],
    "progress": 0,
    "processed": 0,
    "total": 100000
}

def run_scraper():
    current_job["is_running"] = True
    current_job["logs"] = []
    current_job["processed"] = 0
    current_job["progress"] = 0
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "civitai_mass_scraper.py")
    
    # We use unbuffered output
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            if not line:
                continue
                
            # Simple parsing for progress
            if "Processed:" in line:
                try:
                    p_str = line.split("Processed:")[1].split(")")[0].strip()
                    current_job["processed"] = int(p_str)
                    current_job["progress"] = min(100, int((current_job["processed"] / current_job["total"]) * 100))
                except Exception:
                    pass
            
            level = "INFO"
            if "Error" in line or "Traceback" in line:
                level = "ERROR"
            elif "Rate limited" in line:
                level = "WARN"
            elif "Complete" in line:
                level = "DONE"
                
            current_job["logs"].append({
                "id": time.time(),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": line
            })
            
            if len(current_job["logs"]) > 100:
                current_job["logs"].pop(0)
                
    current_job["is_running"] = False
    current_job["logs"].append({
        "id": time.time(),
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "level": "DONE",
        "message": f"Sync script finished with exit code {process.returncode}."
    })

@router.post("/start")
async def start_sync(background_tasks: BackgroundTasks):
    if current_job["is_running"]:
        return {"status": "already_running"}
        
    background_tasks.add_task(run_scraper)
    return {"status": "started"}

@router.get("/status")
async def get_status():
    return current_job

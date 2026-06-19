from fastapi import APIRouter, BackgroundTasks
import subprocess
import time
import sys
import os
import datetime
import json

router = APIRouter(prefix="/api/admin/sync", tags=["admin"])

# Global state for sync jobs
current_job = {
    "is_running": False,
    "logs": [],
    "progress": 0,
    "processed": 0,
    "total": 100000,
    "speed": 0,
    "eta": "~"
}

# Store process globally to allow cancellation
active_process = None

def get_state_file_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper_state.json")

def load_initial_processed():
    state_file = get_state_file_path()
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                return state.get("total_processed", 0)
        except Exception:
            return 0
    return 0

def run_scraper():
    global active_process
    current_job["is_running"] = True
    current_job["logs"] = []
    
    # Load initial processed count
    initial_processed = load_initial_processed()
    current_job["processed"] = initial_processed
    current_job["progress"] = min(100, int((initial_processed / current_job["total"]) * 100))
    
    start_time = time.time()
    start_processed = initial_processed
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "civitai_mass_scraper.py")
    
    # We use unbuffered output
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    active_process = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    while True:
        line = active_process.stdout.readline()
        if not line and active_process.poll() is not None:
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
                    
                    # Calculate speed and ETA
                    elapsed_minutes = (time.time() - start_time) / 60.0
                    if elapsed_minutes > 0.1: # avoid divide by zero or wild spikes at start
                        records_done = current_job["processed"] - start_processed
                        if records_done > 0:
                            speed = records_done / elapsed_minutes
                            current_job["speed"] = int(speed)
                            remaining = current_job["total"] - current_job["processed"]
                            eta_mins = int(remaining / speed)
                            current_job["eta"] = f"~{eta_mins} min remaining"
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
    active_process = None
    current_job["logs"].append({
        "id": time.time(),
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "level": "DONE",
        "message": "Sync script stopped or finished."
    })

@router.post("/start")
async def start_sync(background_tasks: BackgroundTasks):
    if current_job["is_running"]:
        return {"status": "already_running"}
        
    background_tasks.add_task(run_scraper)
    return {"status": "started"}

@router.post("/pause")
async def pause_sync():
    global active_process
    if active_process and current_job["is_running"]:
        active_process.terminate()
        active_process = None
        current_job["is_running"] = False
        current_job["speed"] = 0
        current_job["eta"] = "Paused"
        return {"status": "paused"}
    return {"status": "not_running"}

@router.post("/reset")
async def reset_sync():
    global active_process
    if active_process and current_job["is_running"]:
        active_process.terminate()
        active_process = None
        current_job["is_running"] = False
        
    # Delete state file
    state_file = get_state_file_path()
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
        except Exception:
            pass
            
    current_job["processed"] = 0
    current_job["progress"] = 0
    current_job["speed"] = 0
    current_job["eta"] = "~"
    current_job["logs"] = []
    return {"status": "reset"}

@router.get("/status")
async def get_status():
    if not current_job["is_running"] and current_job["processed"] == 0:
        current_job["processed"] = load_initial_processed()
        current_job["progress"] = min(100, int((current_job["processed"] / current_job["total"]) * 100))
    return current_job

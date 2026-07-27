import os
import sys
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RunLogger:

    def __init__(self, topic: str, logs_dir: str = "./logs"):
        self.topic = topic
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_filename = os.path.join(self.logs_dir, f"run_log_{self.timestamp}.json")
        self.history = {
            "topic": topic,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "transitions": []
        }

    def log_step(self, step_name: str, status: str, details: dict):
        """Record a pipeline step execution."""
        entry = {
            "step_name": step_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "details": details
        }
        self.history["transitions"].append(entry)
        self._flush()
        print(f"📌 [LOG][{step_name.upper()}] Status: {status} | Details: {list(details.keys())}")

    def _flush(self):
        """Write current log history to JSON file."""
        with open(self.log_filename, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def finalize(self, final_report: str):
        """Mark completion and record final report."""
        self.history["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history["final_report"] = final_report
        self._flush()
        print(f"\n✅ Log saved to: {self.log_filename}")

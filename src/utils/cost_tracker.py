import os
import json
import csv
from datetime import datetime

class CostTracker:
    def __init__(self, log_path="corpus/logs/cost_log.csv"):
        self.log_path = log_path
        self._ensure_log_exists()

    def _ensure_log_exists(self):
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "provider", "endpoint", "requests", "estimated_cost_usd", "notes"])

    def log_cost(self, provider, endpoint, requests, cost_usd=0.0, notes=""):
        timestamp = datetime.now().isoformat()
        with open(self.log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, provider, endpoint, requests, cost_usd, notes])

cost_tracker = CostTracker()

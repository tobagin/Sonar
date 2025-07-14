"""
Data models for the Echo webhook inspector application.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WebhookRequest(BaseModel):
    """Model representing a received webhook request."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    method: str
    path: str
    headers: dict[str, str]
    body: str | bytes | dict[str, Any]
    query_params: dict[str, str]
    content_type: str | None = None
    content_length: int | None = None

    def __str__(self) -> str:
        """String representation of the webhook request."""
        return f"{self.method} {self.path} at {self.timestamp.strftime('%H:%M:%S')}"

    @property
    def formatted_body(self) -> str:
        """Format the body for display."""
        if isinstance(self.body, bytes):
            try:
                return self.body.decode('utf-8')
            except UnicodeDecodeError:
                return f"<binary data: {len(self.body)} bytes>"
        elif isinstance(self.body, dict):
            import json
            return json.dumps(self.body, indent=2)
        return str(self.body)

    @property
    def formatted_headers(self) -> str:
        """Format headers for display."""
        return '\n'.join(f"{k}: {v}" for k, v in self.headers.items())


class TunnelStatus(BaseModel):
    """Model representing the current tunnel status."""

    active: bool = False
    public_url: str | None = None
    start_time: datetime | None = None
    error: str | None = None

    def __str__(self) -> str:
        """String representation of tunnel status."""
        if self.active and self.public_url:
            return f"Active: {self.public_url}"
        elif self.error:
            return f"Error: {self.error}"
        return "Inactive"


class RequestStorage:
    """Storage for webhook requests with persistent history support."""

    def __init__(self, max_history: int = 1000, data_dir: str | None = None) -> None:
        """Initialize the storage.
        
        Args:
            max_history (int): Maximum number of requests to keep in history.
            data_dir (str | None): Directory to store persistent data. If None, uses default.
        """
        self._requests: list[WebhookRequest] = []  # Active requests
        self._history: list[WebhookRequest] = []   # Cleared requests history
        self._max_requests = 1000  # Limit to prevent memory issues
        self._max_history = max_history
        
        # Set up persistent storage
        if data_dir is None:
            data_dir = os.path.expanduser("~/.local/share/echo")
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._data_dir / "history.json"
        
        # Load existing history from disk
        self._load_history_from_disk()

    def add_request(self, request: WebhookRequest) -> None:
        """Add a new request to storage."""
        self._requests.append(request)

        # Remove oldest requests if we exceed the limit
        if len(self._requests) > self._max_requests:
            self._requests = self._requests[-self._max_requests:]

    def get_requests(self) -> list[WebhookRequest]:
        """Get all active requests."""
        return self._requests.copy()

    def get_history(self) -> list[WebhookRequest]:
        """Get all requests from history."""
        return self._history.copy()

    def get_request_by_id(self, request_id: str) -> WebhookRequest | None:
        """Get a specific request by ID from active requests."""
        for request in self._requests:
            if request.id == request_id:
                return request
        return None

    def get_history_request_by_id(self, request_id: str) -> WebhookRequest | None:
        """Get a specific request by ID from history."""
        for request in self._history:
            if request.id == request_id:
                return request
        return None

    def clear(self) -> None:
        """Clear active requests (moves them to history)."""
        # Move current requests to history (most recent first)
        for request in reversed(self._requests):
            self._history.insert(0, request)
        
        # Limit history size
        if len(self._history) > self._max_history:
            self._history = self._history[:self._max_history]
        
        # Clear active requests
        self._requests.clear()
        
        # Save to disk
        self._save_history_to_disk()

    def clear_history(self) -> None:
        """Permanently clear all history."""
        self._history.clear()
        # Save to disk (empty history)
        self._save_history_to_disk()

    def remove_from_history(self, request_id: str) -> bool:
        """Remove a specific request from history.
        
        Args:
            request_id (str): The ID of the request to remove.
            
        Returns:
            bool: True if removed, False if not found.
        """
        for i, request in enumerate(self._history):
            if request.id == request_id:
                del self._history[i]
                # Save to disk
                self._save_history_to_disk()
                return True
        return False

    def restore_from_history(self, request_id: str) -> bool:
        """Restore a request from history to active requests.
        
        Args:
            request_id (str): The ID of the request to restore.
            
        Returns:
            bool: True if restored, False if not found.
        """
        for i, request in enumerate(self._history):
            if request.id == request_id:
                # Move to active requests
                restored_request = self._history.pop(i)
                self._requests.insert(0, restored_request)
                # Save updated history to disk
                self._save_history_to_disk()
                return True
        return False

    def count(self) -> int:
        """Get the number of active requests."""
        return len(self._requests)

    def count_history(self) -> int:
        """Get the number of requests in history."""
        return len(self._history)

    def get_total_count(self) -> int:
        """Get the total number of requests (active + history)."""
        return len(self._requests) + len(self._history)

    def get_latest(self, limit: int = 10) -> list[WebhookRequest]:
        """Get the latest N active requests."""
        return self._requests[-limit:] if self._requests else []

    def _load_history_from_disk(self) -> None:
        """Load history from persistent storage."""
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    
                # Convert JSON data back to WebhookRequest objects
                for item in history_data:
                    try:
                        # Convert timestamp string back to datetime
                        if isinstance(item.get('timestamp'), str):
                            item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                        
                        request = WebhookRequest(**item)
                        self._history.append(request)
                    except Exception as e:
                        # Skip corrupted entries but continue loading others
                        continue
                
                # Ensure we don't exceed max history
                if len(self._history) > self._max_history:
                    self._history = self._history[:self._max_history]
                    
        except Exception as e:
            # If loading fails, start with empty history
            self._history = []

    def _save_history_to_disk(self) -> None:
        """Save history to persistent storage."""
        try:
            # Convert WebhookRequest objects to JSON-serializable format
            history_data = []
            for request in self._history:
                data = request.model_dump()
                # Convert datetime to ISO string for JSON serialization
                if isinstance(data.get('timestamp'), datetime):
                    data['timestamp'] = data['timestamp'].isoformat()
                history_data.append(data)
            
            # Write to temporary file first, then rename for atomicity
            temp_file = self._history_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            temp_file.replace(self._history_file)
            
        except Exception as e:
            # Log error but don't crash the application
            pass

    def search_history(self, query: str, method: str | None = None, 
                      date_from: datetime | None = None, 
                      date_to: datetime | None = None) -> list[WebhookRequest]:
        """Search history with various filters.
        
        Args:
            query (str): Search query for path, headers, or body content.
            method (str | None): Filter by HTTP method.
            date_from (datetime | None): Filter requests from this date.
            date_to (datetime | None): Filter requests until this date.
            
        Returns:
            list[WebhookRequest]: Filtered history requests.
        """
        results = []
        query_lower = query.lower() if query else ""
        
        for request in self._history:
            # Filter by method
            if method and request.method.upper() != method.upper():
                continue
            
            # Filter by date range
            if date_from and request.timestamp < date_from:
                continue
            if date_to and request.timestamp > date_to:
                continue
            
            # Filter by query in path, headers, or body
            if query_lower:
                searchable_text = (
                    request.path.lower() +
                    " " + str(request.headers).lower() +
                    " " + str(request.formatted_body).lower()
                )
                if query_lower not in searchable_text:
                    continue
            
            results.append(request)
        
        return results

    def get_history_stats(self) -> dict[str, Any]:
        """Get statistics about the request history.
        
        Returns:
            dict[str, Any]: Statistics including method counts, date ranges, etc.
        """
        if not self._history:
            return {
                "total_requests": 0,
                "methods": {},
                "date_range": None,
                "most_common_paths": [],
                "average_requests_per_day": 0
            }
        
        # Count methods
        method_counts = {}
        path_counts = {}
        
        for request in self._history:
            method_counts[request.method] = method_counts.get(request.method, 0) + 1
            path_counts[request.path] = path_counts.get(request.path, 0) + 1
        
        # Get date range
        timestamps = [req.timestamp for req in self._history]
        date_range = {
            "earliest": min(timestamps),
            "latest": max(timestamps),
            "span_days": (max(timestamps) - min(timestamps)).days + 1
        }
        
        # Most common paths
        most_common_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Average requests per day
        avg_per_day = len(self._history) / max(date_range["span_days"], 1)
        
        return {
            "total_requests": len(self._history),
            "methods": method_counts,
            "date_range": date_range,
            "most_common_paths": most_common_paths,
            "average_requests_per_day": round(avg_per_day, 2)
        }

    def export_history(self, filepath: str, format: str = "json") -> bool:
        """Export history to file.
        
        Args:
            filepath (str): Path to export file.
            format (str): Export format ("json", "csv", or "txt").
            
        Returns:
            bool: True if export succeeded, False otherwise.
        """
        try:
            filepath = Path(filepath)
            
            if format.lower() == "json":
                return self._export_json(filepath)
            elif format.lower() == "csv":
                return self._export_csv(filepath)
            elif format.lower() == "txt":
                return self._export_txt(filepath)
            else:
                return False
                
        except Exception:
            return False

    def _export_json(self, filepath: Path) -> bool:
        """Export history as JSON."""
        try:
            history_data = []
            for request in self._history:
                data = request.model_dump()
                if isinstance(data.get('timestamp'), datetime):
                    data['timestamp'] = data['timestamp'].isoformat()
                history_data.append(data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _export_csv(self, filepath: Path) -> bool:
        """Export history as CSV."""
        try:
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Method', 'Path', 'Content-Type', 'Body'])
                
                for request in self._history:
                    writer.writerow([
                        request.timestamp.isoformat(),
                        request.method,
                        request.path,
                        request.content_type or '',
                        request.formatted_body[:1000] + '...' if len(request.formatted_body) > 1000 else request.formatted_body
                    ])
            return True
        except Exception:
            return False

    def _export_txt(self, filepath: Path) -> bool:
        """Export history as plain text."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Echo Webhook Request History\n")
                f.write("=" * 50 + "\n\n")
                
                for i, request in enumerate(self._history, 1):
                    f.write(f"Request #{i}\n")
                    f.write(f"Timestamp: {request.timestamp}\n")
                    f.write(f"Method: {request.method}\n")
                    f.write(f"Path: {request.path}\n")
                    f.write(f"Content-Type: {request.content_type or 'N/A'}\n")
                    f.write("Headers:\n")
                    for key, value in request.headers.items():
                        f.write(f"  {key}: {value}\n")
                    f.write(f"Body:\n{request.formatted_body}\n")
                    f.write("-" * 50 + "\n\n")
            return True
        except Exception:
            return False

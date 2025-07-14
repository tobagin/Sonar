"""
Tests for the models module.
"""

import json
from datetime import datetime

import pytest

from src.models import RequestStorage, TunnelStatus, WebhookRequest


class TestWebhookRequest:
    """Test WebhookRequest model."""
    
    def test_webhook_request_creation(self):
        """Test creating webhook request."""
        req = WebhookRequest(
            method="POST",
            path="/webhook/test",
            headers={"Content-Type": "application/json"},
            body='{"test": true}',
            query_params={"param": "value"}
        )
        
        assert req.method == "POST"
        assert req.path == "/webhook/test"
        assert req.headers["Content-Type"] == "application/json"
        assert req.body == '{"test": true}'
        assert req.query_params["param"] == "value"
        assert req.id is not None
        assert isinstance(req.timestamp, datetime)
    
    def test_webhook_request_defaults(self):
        """Test webhook request with default values."""
        req = WebhookRequest(
            method="GET",
            path="/test",
            headers={},
            body="",
            query_params={}
        )
        
        assert req.content_type is None
        assert req.content_length is None
        assert req.id is not None
        assert isinstance(req.timestamp, datetime)
    
    def test_webhook_request_str(self):
        """Test string representation."""
        fixed_time = datetime(2025, 1, 1, 12, 30, 45)
        
        req = WebhookRequest(
            method="POST",
            path="/api/webhook",
            headers={},
            body="",
            query_params={},
            timestamp=fixed_time
        )
        
        assert str(req) == "POST /api/webhook at 12:30:45"
    
    def test_formatted_body_json_dict(self):
        """Test formatted body with JSON dict."""
        req = WebhookRequest(
            method="POST",
            path="/test",
            headers={},
            body={"key": "value", "nested": {"data": 123}},
            query_params={}
        )
        
        formatted = req.formatted_body
        assert isinstance(formatted, str)
        assert "key" in formatted
        assert "value" in formatted
    
    def test_formatted_body_bytes(self):
        """Test formatted body with bytes."""
        req = WebhookRequest(
            method="POST",
            path="/test",
            headers={},
            body=b"test data",
            query_params={}
        )
        
        assert req.formatted_body == "test data"
    
    def test_formatted_body_binary_bytes(self):
        """Test formatted body with binary bytes."""
        # Use bytes that will cause UnicodeDecodeError
        binary_data = b"\xff\xfe\xfd\xfc"
        req = WebhookRequest(
            method="POST",
            path="/test",
            headers={},
            body=binary_data,
            query_params={}
        )
        
        formatted = req.formatted_body
        assert "<binary data: 4 bytes>" in formatted
    
    def test_formatted_headers(self):
        """Test formatted headers."""
        req = WebhookRequest(
            method="POST",
            path="/test",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token",
                "User-Agent": "Test/1.0"
            },
            body="",
            query_params={}
        )
        
        formatted = req.formatted_headers
        assert "Content-Type: application/json" in formatted
        assert "Authorization: Bearer token" in formatted
        assert "User-Agent: Test/1.0" in formatted


class TestTunnelStatus:
    """Test TunnelStatus model."""
    
    def test_tunnel_status_inactive(self):
        """Test inactive tunnel status."""
        status = TunnelStatus()
        
        assert status.active is False
        assert status.public_url is None
        assert status.start_time is None
        assert status.error is None
        assert str(status) == "Inactive"
    
    def test_tunnel_status_active(self):
        """Test active tunnel status."""
        status = TunnelStatus(
            active=True,
            public_url="https://abc123.ngrok.io",
            start_time=datetime.now()
        )
        
        assert status.active is True
        assert status.public_url == "https://abc123.ngrok.io"
        assert str(status) == "Active: https://abc123.ngrok.io"
    
    def test_tunnel_status_error(self):
        """Test error tunnel status."""
        status = TunnelStatus(
            active=False,
            error="Connection failed"
        )
        
        assert str(status) == "Error: Connection failed"


class TestRequestStorage:
    """Test RequestStorage class."""
    
    def test_storage_initialization(self):
        """Test storage initialization."""
        storage = RequestStorage()
        
        assert storage.count() == 0
        assert storage.get_requests() == []
    
    def test_add_request(self):
        """Test adding requests."""
        storage = RequestStorage()
        
        req1 = WebhookRequest(
            method="GET",
            path="/test1",
            headers={},
            body="",
            query_params={}
        )
        
        req2 = WebhookRequest(
            method="POST",
            path="/test2",
            headers={},
            body="data",
            query_params={}
        )
        
        storage.add_request(req1)
        storage.add_request(req2)
        
        assert storage.count() == 2
        requests = storage.get_requests()
        assert len(requests) == 2
        assert requests[0] == req1
        assert requests[1] == req2
    
    def test_get_request_by_id(self):
        """Test getting request by ID."""
        storage = RequestStorage()
        
        req = WebhookRequest(
            method="GET",
            path="/test",
            headers={},
            body="",
            query_params={}
        )
        
        storage.add_request(req)
        
        found = storage.get_request_by_id(req.id)
        assert found == req
        
        not_found = storage.get_request_by_id("nonexistent")
        assert not_found is None
    
    def test_clear_requests(self):
        """Test clearing requests."""
        storage = RequestStorage()
        
        req = WebhookRequest(
            method="GET",
            path="/test",
            headers={},
            body="",
            query_params={}
        )
        
        storage.add_request(req)
        assert storage.count() == 1
        
        storage.clear()
        assert storage.count() == 0
        assert storage.get_requests() == []
    
    def test_get_latest_requests(self):
        """Test getting latest requests."""
        storage = RequestStorage()
        
        # Add multiple requests
        for i in range(5):
            req = WebhookRequest(
                method="GET",
                path=f"/test{i}",
                headers={},
                body="",
                query_params={}
            )
            storage.add_request(req)
        
        latest = storage.get_latest(3)
        assert len(latest) == 3
        # Should get the last 3 requests
        assert latest[0].path == "/test2"
        assert latest[1].path == "/test3"
        assert latest[2].path == "/test4"
    
    def test_max_requests_limit(self):
        """Test maximum requests limit."""
        storage = RequestStorage()
        storage._max_requests = 3  # Set low limit for testing
        
        # Add more than the limit
        for i in range(5):
            req = WebhookRequest(
                method="GET",
                path=f"/test{i}",
                headers={},
                body="",
                query_params={}
            )
            storage.add_request(req)
        
        # Should only keep the last 3
        assert storage.count() == 3
        requests = storage.get_requests()
        assert requests[0].path == "/test2"  # Oldest kept
        assert requests[1].path == "/test3"
        assert requests[2].path == "/test4"  # Newest
"""
Tests for the server module.
"""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.models import RequestStorage
from src.server import WebhookServer


class TestWebhookServer:
    """Test WebhookServer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RequestStorage()
        self.server = WebhookServer(self.storage)
    
    def test_server_initialization(self):
        """Test server initialization."""
        assert self.server.storage == self.storage
        assert self.server.app is not None
        assert self.server.port == 8000
        assert self.server.host == "127.0.0.1"
        assert self.server.is_running is False
    
    def test_webhook_endpoint_get(self):
        """Test webhook endpoint with GET request."""
        client = TestClient(self.server.app)
        
        response = client.get("/webhook")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "request_id" in data
        assert "timestamp" in data
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.method == "GET"
        assert request.path == "/webhook"
    
    def test_webhook_endpoint_post_json(self):
        """Test webhook endpoint with POST JSON."""
        client = TestClient(self.server.app)
        
        test_data = {"key": "value", "number": 123}
        response = client.post(
            "/webhook",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.method == "POST"
        assert request.body == test_data
        assert request.content_type == "application/json"
    
    def test_webhook_endpoint_post_form(self):
        """Test webhook endpoint with form data."""
        client = TestClient(self.server.app)
        
        form_data = {"field1": "value1", "field2": "value2"}
        response = client.post("/webhook", data=form_data)
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.method == "POST"
        assert "field1=value1" in request.body
    
    def test_webhook_endpoint_with_path(self):
        """Test webhook endpoint with custom path."""
        client = TestClient(self.server.app)
        
        response = client.post("/webhook/custom/path/here")
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.path == "/custom/path/here"
    
    def test_webhook_endpoint_with_query_params(self):
        """Test webhook endpoint with query parameters."""
        client = TestClient(self.server.app)
        
        response = client.get("/webhook?param1=value1&param2=value2")
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.query_params["param1"] == "value1"
        assert request.query_params["param2"] == "value2"
    
    def test_webhook_endpoint_all_methods(self):
        """Test webhook endpoint with various HTTP methods."""
        client = TestClient(self.server.app)
        
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            response = client.request(method, "/webhook")
            assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == len(methods)
        requests = self.storage.get_requests()
        stored_methods = [req.method for req in requests]
        assert stored_methods == methods
    
    def test_request_callback(self):
        """Test request callback functionality."""
        callback_mock = Mock()
        self.server.set_request_callback(callback_mock)
        
        client = TestClient(self.server.app)
        response = client.get("/webhook")
        
        assert response.status_code == 200
        callback_mock.assert_called_once()
        
        # Check the callback was called with correct request
        call_args = callback_mock.call_args[0]
        request = call_args[0]
        assert request.method == "GET"
        assert request.path == "/webhook"
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        client = TestClient(self.server.app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Echo Webhook Server"
        assert data["version"] == "1.0.0"
        assert "/webhook" in data["endpoints"]
    
    def test_health_endpoint(self):
        """Test health endpoint."""
        client = TestClient(self.server.app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_server_url_property(self):
        """Test server URL property."""
        server = WebhookServer(self.storage)
        
        assert server.url == "http://127.0.0.1:8000"
        
        # Test with custom host/port
        server.host = "localhost"
        server.port = 9000
        assert server.url == "http://localhost:9000"
    
    @patch('src.server.uvicorn.Server')
    @patch('src.server.threading.Thread')
    def test_server_start(self, mock_thread, mock_uvicorn_server):
        """Test server start method."""
        mock_server_instance = Mock()
        mock_uvicorn_server.return_value = mock_server_instance
        
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        self.server.start(port=9000, host="localhost")
        
        assert self.server.port == 9000
        assert self.server.host == "localhost"
        mock_thread_instance.start.assert_called_once()
    
    def test_server_stop_not_running(self):
        """Test stopping server when not running."""
        # Should not raise any errors
        self.server.stop()
        assert not self.server.is_running
    
    def test_binary_data_handling(self):
        """Test handling of binary data."""
        client = TestClient(self.server.app)
        
        binary_data = b"\x00\x01\x02\x03\x04"
        response = client.post(
            "/webhook",
            content=binary_data,
            headers={"Content-Type": "application/octet-stream"}
        )
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == binary_data
        assert request.content_type == "application/octet-stream"
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON."""
        client = TestClient(self.server.app)
        
        malformed_json = '{"incomplete": json'
        response = client.post(
            "/webhook",
            content=malformed_json,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        
        # Check storage - should store as string
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == malformed_json
    
    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        client = TestClient(self.server.app)
        
        # Create a large JSON payload (1MB)
        large_data = {"data": "x" * (1024 * 1024)}
        response = client.post("/webhook", json=large_data)
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == large_data
        assert request.content_length is not None
        assert request.content_length > 1000000  # Should be > 1MB
    
    def test_empty_body_handling(self):
        """Test handling of empty request bodies."""
        client = TestClient(self.server.app)
        
        response = client.post("/webhook", content="")
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == ""
    
    def test_special_characters_in_path(self):
        """Test handling of special characters in path."""
        client = TestClient(self.server.app)
        
        # Test various special characters
        special_paths = [
            "/webhook/test%20space",
            "/webhook/test-dash_underscore",
            "/webhook/test.period",
        ]
        
        for path in special_paths:
            response = client.get(path)
            assert response.status_code == 200
        
        assert self.storage.count() == len(special_paths)
    
    def test_various_content_types(self):
        """Test handling of various content types."""
        client = TestClient(self.server.app)
        
        content_types = [
            ("text/plain", "plain text data"),
            ("application/xml", "<xml><data>test</data></xml>"),
            ("text/html", "<html><body>test</body></html>"),
            ("application/x-www-form-urlencoded", "key=value&other=data"),
        ]
        
        for content_type, data in content_types:
            response = client.post(
                "/webhook",
                content=data,
                headers={"Content-Type": content_type}
            )
            assert response.status_code == 200
        
        assert self.storage.count() == len(content_types)
        requests = self.storage.get_requests()
        
        for i, (expected_type, expected_data) in enumerate(content_types):
            assert requests[i].content_type == expected_type
            assert requests[i].body == expected_data
    
    def test_multiple_headers(self):
        """Test handling of multiple custom headers."""
        client = TestClient(self.server.app)
        
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "Authorization": "Bearer token123",
            "User-Agent": "TestClient/1.0",
            "X-Request-ID": "12345",
            "Content-Type": "application/json"
        }
        
        response = client.post(
            "/webhook",
            json={"test": "data"},
            headers=custom_headers
        )
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        
        # Verify all custom headers are stored
        for header_name, header_value in custom_headers.items():
            assert header_name.lower() in request.headers
            assert request.headers[header_name.lower()] == header_value
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        client = TestClient(self.server.app)
        
        import concurrent.futures
        
        def make_request(i):
            return client.post("/webhook", json={"request_id": i})
        
        # Send 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # All requests should be stored
        assert self.storage.count() == 10
    
    def test_very_long_headers(self):
        """Test handling of very long header values."""
        client = TestClient(self.server.app)
        
        long_value = "x" * 10000  # 10KB header value
        response = client.post(
            "/webhook",
            json={"test": "data"},
            headers={"X-Very-Long-Header": long_value}
        )
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.headers["x-very-long-header"] == long_value
    
    def test_webhook_with_deep_json_nesting(self):
        """Test handling of deeply nested JSON structures."""
        client = TestClient(self.server.app)
        
        # Create deeply nested JSON
        nested_data = {"level1": {"level2": {"level3": {"level4": {"data": "deep"}}}}}
        response = client.post("/webhook", json=nested_data)
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == nested_data
    
    def test_callback_exception_handling(self):
        """Test that callback exceptions don't crash the server."""
        def failing_callback(request):
            raise Exception("Callback failed!")
        
        self.server.set_request_callback(failing_callback)
        
        client = TestClient(self.server.app)
        response = client.get("/webhook")
        
        # Server should still respond successfully
        assert response.status_code == 200
        
        # Request should still be stored
        assert self.storage.count() == 1
    
    def test_unicode_data_handling(self):
        """Test handling of unicode data in requests."""
        client = TestClient(self.server.app)
        
        unicode_data = {
            "emoji": "🚀💻🔥",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "åäöüñç"
        }
        
        response = client.post("/webhook", json=unicode_data)
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == unicode_data
    
    def test_no_content_length_header(self):
        """Test requests without Content-Length header."""
        client = TestClient(self.server.app)
        
        # This simulates chunked transfer encoding
        response = client.post(
            "/webhook",
            content="test data without content-length"
        )
        
        assert response.status_code == 200
        
        # Check storage
        assert self.storage.count() == 1
        request = self.storage.get_requests()[0]
        assert request.body == "test data without content-length"
    
    @patch('src.server.uvicorn.Server')
    @patch('src.server.threading.Thread')
    def test_server_start_stop_lifecycle(self, mock_thread, mock_uvicorn_server):
        """Test complete server lifecycle."""
        mock_server_instance = Mock()
        mock_uvicorn_server.return_value = mock_server_instance
        
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Test starting server
        self.server.start()
        mock_thread_instance.start.assert_called_once()
        
        # Test stopping server
        self.server._server = mock_server_instance
        self.server._server_thread = mock_thread_instance
        self.server.is_running = True
        
        self.server.stop()
        mock_server_instance.shutdown.assert_called_once()
    
    def test_request_id_uniqueness(self):
        """Test that each request gets a unique ID."""
        client = TestClient(self.server.app)
        
        # Make multiple requests
        for i in range(5):
            response = client.get(f"/webhook?test={i}")
            assert response.status_code == 200
        
        # Check all request IDs are unique
        requests = self.storage.get_requests()
        request_ids = [req.id for req in requests]
        assert len(set(request_ids)) == len(request_ids)  # All unique
    
    def test_timestamp_accuracy(self):
        """Test that request timestamps are accurate."""
        import time
        from datetime import datetime, timedelta
        
        client = TestClient(self.server.app)
        
        before_request = datetime.now()
        response = client.get("/webhook")
        after_request = datetime.now()
        
        assert response.status_code == 200
        
        # Check timestamp is within reasonable range
        request = self.storage.get_requests()[0]
        assert before_request <= request.timestamp <= after_request
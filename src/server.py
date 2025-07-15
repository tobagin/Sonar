"""
FastAPI server for receiving webhook requests.
"""

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .models import RequestStorage, WebhookRequest
from .input_sanitizer import sanitize_webhook_data

logger = logging.getLogger(__name__)


class WebhookServer:
    """FastAPI server for receiving webhook requests."""

    def __init__(self, request_storage: RequestStorage) -> None:
        """Initialize the webhook server."""
        self.storage = request_storage
        self.app = FastAPI(title="Sonar Webhook Server", version="1.0.4")
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None
        self.port = 8000
        self.host = "127.0.0.1"
        self.is_running = False

        # Callback for new requests
        self.on_request_received: Callable[[WebhookRequest], None] | None = None

        # Set up routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up FastAPI routes."""

        @self.app.get("/health")
        async def health() -> dict[str, str]:
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.app.get("/")
        async def root() -> dict[str, str]:
            """Root endpoint."""
            return {
                "message": "Sonar Webhook Server",
                "version": "1.0.4",
                "info": "Accepts requests on any endpoint path",
                "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                "examples": ["/webhook", "/api/events", "/stripe-webhook", "/github-webhook"]
            }

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        async def receive_any_request(request: Request, path: str, response: Response = Response()) -> dict[str, Any]:
            """Receive webhook requests with input validation and sanitization."""
            try:
                # Skip empty paths (root) to avoid conflicts with specific root route
                if not path:
                    return {"error": "Use specific endpoints for root requests"}
                    
                # Get request body
                body = await request.body()

                # Try to parse JSON body
                parsed_body: Any = body
                content_type = request.headers.get("content-type", "")

                if content_type.startswith("application/json") and body:
                    try:
                        parsed_body = json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        parsed_body = body.decode("utf-8", errors="replace")
                elif content_type.startswith("application/x-www-form-urlencoded") and body:
                    try:
                        parsed_body = body.decode("utf-8")
                    except UnicodeDecodeError:
                        parsed_body = body
                elif body:
                    try:
                        parsed_body = body.decode("utf-8")
                    except UnicodeDecodeError:
                        parsed_body = body
                else:
                    parsed_body = ""

                # Sanitize and validate input data
                request_path = f"/{path}"
                is_valid, sanitized_data, warnings = sanitize_webhook_data(
                    method=request.method,
                    path=request_path,
                    headers=dict(request.headers),
                    body=parsed_body,
                    query_params=dict(request.query_params),
                    content_type=content_type or None,
                    content_length=len(body) if body else None
                )

                # Log warnings if any
                if warnings:
                    logger.warning(f"Webhook validation warnings: {warnings}")

                # Reject invalid requests
                if not is_valid:
                    logger.error(f"Invalid webhook request: {warnings}")
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "message": "Invalid request data",
                            "errors": warnings
                        }
                    )

                # Create webhook request with sanitized data
                webhook_request = WebhookRequest(
                    method=sanitized_data['method'],
                    path=sanitized_data['path'],
                    headers=sanitized_data['headers'],
                    body=sanitized_data['body'],
                    query_params=sanitized_data['query_params'],
                    content_type=sanitized_data['content_type'],
                    content_length=sanitized_data['content_length']
                )

                # Store request
                self.storage.add_request(webhook_request)

                # Notify callback
                if self.on_request_received:
                    try:
                        self.on_request_received(webhook_request)
                    except Exception as e:
                        logger.error(f"Error in request callback: {e}")

                logger.info(f"Received {request.method} request to {webhook_request.path}")

                # Return success response with warnings if any
                response_data = {
                    "status": "received",
                    "message": "Webhook received successfully",
                    "request_id": webhook_request.id,
                    "timestamp": webhook_request.timestamp.isoformat()
                }
                
                if warnings:
                    response_data["warnings"] = warnings

                return response_data

            except Exception as e:
                logger.error(f"Error processing webhook: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": "Internal server error while processing webhook"
                    }
                )

    def start(self, port: int = 8000, host: str = "127.0.0.1") -> None:
        """Start the webhook server in a separate thread."""
        if self.is_running:
            logger.warning("Server is already running")
            return

        self.port = port
        self.host = host

        def run_server() -> None:
            """Run the uvicorn server."""
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False
            )
            self.server = uvicorn.Server(config)

            # Set up event loop for thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                self.is_running = True
                loop.run_until_complete(self.server.serve())
            except Exception as e:
                logger.error(f"Server error: {e}")
            finally:
                self.is_running = False
                loop.close()

        # Start server in separate thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"Webhook server starting on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the webhook server."""
        if not self.is_running or not self.server:
            return

        logger.info("Stopping webhook server...")

        # Signal server to stop
        if self.server:
            self.server.should_exit = True

        # Wait for thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)

        self.is_running = False
        logger.info("Webhook server stopped")

    def set_request_callback(self, callback: Callable[[WebhookRequest], None]) -> None:
        """Set callback for new requests."""
        self.on_request_received = callback

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"

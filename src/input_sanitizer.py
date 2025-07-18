"""
Input validation and sanitization for webhook data.
"""

import html
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote

from .logging_config import get_logger

logger = get_logger(__name__)


class SanitizationConfig:
    """Configuration for input sanitization."""
    
    # Maximum sizes to prevent DoS attacks
    MAX_HEADER_SIZE = 64 * 1024  # 64KB
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB  
    MAX_PATH_LENGTH = 2048  # 2KB
    MAX_QUERY_PARAM_SIZE = 8 * 1024  # 8KB
    MAX_HEADER_COUNT = 100
    MAX_QUERY_PARAM_COUNT = 100
    
    # Maximum nesting depth for JSON
    MAX_JSON_DEPTH = 10
    
    # Patterns for dangerous content
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'data:(?!image/)',  # Data URLs (except images)
        r'vbscript:',  # VBScript URLs
        r'on\w+\s*=',  # Event handlers
        r'eval\s*\(',  # Eval calls
        r'setTimeout\s*\(',  # setTimeout calls
        r'setInterval\s*\(',  # setInterval calls
    ]
    
    # Allowed HTML tags for display (very restrictive)
    ALLOWED_HTML_TAGS = {'b', 'i', 'em', 'strong', 'code', 'pre'}


class WebhookSanitizer:
    """Sanitizes and validates webhook input data."""
    
    def __init__(self, config: Optional[SanitizationConfig] = None):
        self.config = config or SanitizationConfig()
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self.dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.config.DANGEROUS_PATTERNS
        ]
    
    def sanitize_webhook_data(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Any,
        query_params: Dict[str, str],
        content_type: Optional[str] = None,
        content_length: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Sanitize all webhook data.
        
        Returns:
            Tuple of (is_valid, sanitized_data, warnings)
        """
        warnings = []
        sanitized_data = {}
        
        # Validate and sanitize method
        is_valid, sanitized_method, method_warnings = self.sanitize_method(method)
        if not is_valid:
            return False, {}, method_warnings
        sanitized_data['method'] = sanitized_method
        warnings.extend(method_warnings)
        
        # Validate and sanitize path
        is_valid, sanitized_path, path_warnings = self.sanitize_path(path)
        if not is_valid:
            return False, {}, path_warnings
        sanitized_data['path'] = sanitized_path
        warnings.extend(path_warnings)
        
        # Validate and sanitize headers
        is_valid, sanitized_headers, header_warnings = self.sanitize_headers(headers)
        if not is_valid:
            return False, {}, header_warnings
        sanitized_data['headers'] = sanitized_headers
        warnings.extend(header_warnings)
        
        # Validate and sanitize query parameters
        is_valid, sanitized_query, query_warnings = self.sanitize_query_params(query_params)
        if not is_valid:
            return False, {}, query_warnings
        sanitized_data['query_params'] = sanitized_query
        warnings.extend(query_warnings)
        
        # Validate and sanitize body
        is_valid, sanitized_body, body_warnings = self.sanitize_body(
            body, content_type, content_length
        )
        if not is_valid:
            return False, {}, body_warnings
        sanitized_data['body'] = sanitized_body
        warnings.extend(body_warnings)
        
        # Add metadata
        sanitized_data['content_type'] = self.sanitize_string(content_type or "", max_length=256)
        sanitized_data['content_length'] = content_length
        
        return True, sanitized_data, warnings
    
    def sanitize_method(self, method: str) -> Tuple[bool, str, List[str]]:
        """Sanitize HTTP method."""
        if not method:
            return False, "", ["HTTP method is required"]
        
        method = method.upper().strip()
        
        # Check for valid HTTP methods
        valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE'}
        if method not in valid_methods:
            return False, method, [f"Invalid HTTP method: {method}"]
        
        return True, method, []
    
    def sanitize_path(self, path: str) -> Tuple[bool, str, List[str]]:
        """Sanitize URL path."""
        warnings = []
        
        if not path:
            path = "/"
        
        # Check length
        if len(path) > self.config.MAX_PATH_LENGTH:
            return False, path, [f"Path too long: {len(path)} > {self.config.MAX_PATH_LENGTH}"]
        
        try:
            # URL decode
            decoded_path = unquote(path)
            
            # Basic path sanitization
            sanitized_path = self.sanitize_string(decoded_path, check_dangerous=True)
            
            # Ensure it starts with /
            if not sanitized_path.startswith('/'):
                sanitized_path = '/' + sanitized_path
            
            # Check for dangerous patterns
            if self._contains_dangerous_content(sanitized_path):
                warnings.append("Path contains potentially dangerous content")
                # For paths, we'll log but allow (since it's just for display)
            
            return True, sanitized_path, warnings
            
        except Exception as e:
            logger.error(f"Error sanitizing path: {e}")
            return False, path, [f"Error processing path: {str(e)}"]
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Tuple[bool, Dict[str, str], List[str]]:
        """Sanitize HTTP headers."""
        warnings = []
        sanitized_headers = {}
        
        if not headers:
            return True, {}, []
        
        # Check header count
        if len(headers) > self.config.MAX_HEADER_COUNT:
            return False, {}, [f"Too many headers: {len(headers)} > {self.config.MAX_HEADER_COUNT}"]
        
        total_size = 0
        
        for key, value in headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                warnings.append(f"Non-string header: {key}")
                continue
            
            # Check individual header size
            header_size = len(key) + len(value)
            total_size += header_size
            
            if total_size > self.config.MAX_HEADER_SIZE:
                return False, {}, [f"Headers too large: {total_size} > {self.config.MAX_HEADER_SIZE}"]
            
            # Sanitize header name and value
            sanitized_key = self.sanitize_header_name(key)
            sanitized_value = self.sanitize_string(value, max_length=8192)
            
            if sanitized_key:
                sanitized_headers[sanitized_key] = sanitized_value
        
        return True, sanitized_headers, warnings
    
    def sanitize_header_name(self, name: str) -> str:
        """Sanitize HTTP header name."""
        # Remove any non-ASCII and control characters
        sanitized = ''.join(c for c in name if c.isprintable() and ord(c) < 128)
        
        # Header names should only contain specific characters
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', sanitized)
        
        return sanitized.lower()
    
    def sanitize_query_params(self, params: Dict[str, str]) -> Tuple[bool, Dict[str, str], List[str]]:
        """Sanitize query parameters."""
        warnings = []
        sanitized_params = {}
        
        if not params:
            return True, {}, []
        
        # Check parameter count
        if len(params) > self.config.MAX_QUERY_PARAM_COUNT:
            return False, {}, [f"Too many query parameters: {len(params)} > {self.config.MAX_QUERY_PARAM_COUNT}"]
        
        total_size = 0
        
        for key, value in params.items():
            if not isinstance(key, str) or not isinstance(value, str):
                warnings.append(f"Non-string query parameter: {key}")
                continue
            
            param_size = len(key) + len(value)
            total_size += param_size
            
            if total_size > self.config.MAX_QUERY_PARAM_SIZE:
                return False, {}, [f"Query parameters too large: {total_size} > {self.config.MAX_QUERY_PARAM_SIZE}"]
            
            # Sanitize key and value
            sanitized_key = self.sanitize_string(key, max_length=256)
            sanitized_value = self.sanitize_string(value, max_length=2048, check_dangerous=True)
            
            if self._contains_dangerous_content(sanitized_value):
                warnings.append(f"Query parameter '{sanitized_key}' contains potentially dangerous content")
            
            sanitized_params[sanitized_key] = sanitized_value
        
        return True, sanitized_params, warnings
    
    def sanitize_body(
        self,
        body: Any,
        content_type: Optional[str] = None,
        content_length: Optional[int] = None
    ) -> Tuple[bool, Any, List[str]]:
        """Sanitize request body."""
        warnings = []
        
        if not body:
            return True, "", []
        
        # Check content length
        if content_length and content_length > self.config.MAX_BODY_SIZE:
            return False, body, [f"Body too large: {content_length} > {self.config.MAX_BODY_SIZE}"]
        
        # Handle different body types
        if isinstance(body, bytes):
            return self.sanitize_binary_body(body, content_type)
        elif isinstance(body, dict):
            return self.sanitize_json_body(body)
        elif isinstance(body, str):
            return self.sanitize_text_body(body, content_type)
        else:
            # Convert to string and sanitize
            try:
                body_str = str(body)
                return self.sanitize_text_body(body_str, content_type)
            except Exception as e:
                logger.error(f"Error converting body to string: {e}")
                return False, body, [f"Cannot process body type: {type(body)}"]
    
    def sanitize_binary_body(self, body: bytes, content_type: Optional[str] = None) -> Tuple[bool, bytes, List[str]]:
        """Sanitize binary body data."""
        warnings = []
        
        # Check size
        if len(body) > self.config.MAX_BODY_SIZE:
            return False, body, [f"Binary body too large: {len(body)} > {self.config.MAX_BODY_SIZE}"]
        
        # For binary data, we mainly just check size and log the type
        if content_type:
            if content_type.startswith('image/'):
                warnings.append("Received image data")
            elif content_type.startswith('application/octet-stream'):
                warnings.append("Received binary data")
            elif 'executable' in content_type.lower():
                warnings.append("Received potentially executable content")
        
        return True, body, warnings
    
    def sanitize_json_body(self, body: dict) -> Tuple[bool, dict, List[str]]:
        """Sanitize JSON body data."""
        warnings = []
        
        try:
            # Check depth to prevent deeply nested attacks
            max_depth = self._get_dict_depth(body)
            if max_depth > self.config.MAX_JSON_DEPTH:
                return False, body, [f"JSON too deeply nested: {max_depth} > {self.config.MAX_JSON_DEPTH}"]
            
            # Recursively sanitize the JSON structure
            sanitized_body = self._sanitize_json_recursive(body, warnings)
            
            return True, sanitized_body, warnings
            
        except Exception as e:
            logger.error(f"Error sanitizing JSON body: {e}")
            return False, body, [f"Error processing JSON: {str(e)}"]
    
    def sanitize_text_body(self, body: str, content_type: Optional[str] = None) -> Tuple[bool, str, List[str]]:
        """Sanitize text body data."""
        warnings = []
        
        # Check size
        if len(body) > self.config.MAX_BODY_SIZE:
            return False, body, [f"Text body too large: {len(body)} > {self.config.MAX_BODY_SIZE}"]
        
        # Try to parse as JSON if content type suggests it
        if content_type and 'json' in content_type.lower():
            try:
                parsed_json = json.loads(body)
                return self.sanitize_json_body(parsed_json)
            except json.JSONDecodeError:
                warnings.append("Content-Type suggests JSON but body is not valid JSON")
        
        # Sanitize as text
        sanitized_body = self.sanitize_string(body, check_dangerous=True)
        
        # Check for dangerous content
        if self._contains_dangerous_content(sanitized_body):
            warnings.append("Body contains potentially dangerous content")
        
        return True, sanitized_body, warnings
    
    def sanitize_string(
        self,
        text: str,
        max_length: Optional[int] = None,
        check_dangerous: bool = False
    ) -> str:
        """Sanitize a string value."""
        if not isinstance(text, str):
            text = str(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove other control characters except common whitespace
        text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length] + "..."
        
        # HTML escape for safety (preserves the original for display)
        if check_dangerous:
            # For dangerous content, we'll keep original but mark it
            pass
        
        return text
    
    def _sanitize_json_recursive(self, obj: Any, warnings: List[str], depth: int = 0) -> Any:
        """Recursively sanitize JSON structure."""
        if depth > self.config.MAX_JSON_DEPTH:
            warnings.append(f"JSON nesting truncated at depth {depth}")
            return "..."
        
        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():
                sanitized_key = self.sanitize_string(str(key), max_length=256)
                sanitized_value = self._sanitize_json_recursive(value, warnings, depth + 1)
                sanitized[sanitized_key] = sanitized_value
            return sanitized
        
        elif isinstance(obj, list):
            return [self._sanitize_json_recursive(item, warnings, depth + 1) for item in obj]
        
        elif isinstance(obj, str):
            sanitized = self.sanitize_string(obj, max_length=10000)
            if self._contains_dangerous_content(sanitized):
                warnings.append("JSON contains potentially dangerous string content")
            return sanitized
        
        else:
            # Numbers, booleans, null - return as-is
            return obj
    
    def _get_dict_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate the maximum depth of a nested dictionary."""
        if not isinstance(obj, (dict, list)):
            return depth
        
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._get_dict_depth(value, depth + 1) for value in obj.values())
        
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._get_dict_depth(item, depth + 1) for item in obj)
        
        return depth
    
    def _contains_dangerous_content(self, text: str) -> bool:
        """Check if text contains potentially dangerous patterns."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check compiled patterns
        for pattern in self.dangerous_patterns:
            if pattern.search(text):
                return True
        
        return False


# Global sanitizer instance
webhook_sanitizer = WebhookSanitizer()


def sanitize_webhook_data(
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Any,
    query_params: Dict[str, str],
    content_type: Optional[str] = None,
    content_length: Optional[int] = None
) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Convenience function for sanitizing webhook data."""
    return webhook_sanitizer.sanitize_webhook_data(
        method, path, headers, body, query_params, content_type, content_length
    )


def sanitize_for_display(text: str, max_length: int = 1000) -> str:
    """Sanitize text for safe display in the UI."""
    if not isinstance(text, str):
        text = str(text)
    
    # Remove null bytes and control characters but keep the original text
    # (GTK TextView is safe for displaying text without HTML escaping)
    sanitized = text.replace('\x00', '')
    sanitized = ''.join(c for c in sanitized if c.isprintable() or c in '\n\r\t')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized
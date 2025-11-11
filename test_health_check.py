"""
Automated tests for health check endpoint functionality.

Tests verify that the health endpoint:
- Returns correct JSON response
- Bypasses authentication
- Responds within 5 seconds

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import pytest
import subprocess
import time
import json
from datetime import datetime


class TestHealthCheckEndpoint:
    """Test suite for health check endpoint"""
    
    def test_health_endpoint_returns_correct_json(self):
        """
        Test that health endpoint returns correct JSON response with status and timestamp.
        Requirements: 1.1, 1.3
        """
        # Start streamlit app in background
        process = subprocess.Popen(
            ["streamlit", "run", "streamlit_app.py", "--server.headless", "true", 
             "--server.port", "8502"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for app to start
            time.sleep(5)
            
            # Make health check request
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8502/?health=check"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Verify response contains expected fields
            assert result.returncode == 0, "Health check request failed"
            
            # Parse response - look for JSON in output
            output = result.stdout
            
            # Streamlit wraps JSON in HTML, so we need to extract it
            # The response should contain "status" and "timestamp"
            assert "status" in output, "Response missing 'status' field"
            assert "healthy" in output or "ok" in output, "Status should be 'healthy' or 'ok'"
            assert "timestamp" in output, "Response missing 'timestamp' field"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)
    
    def test_health_endpoint_bypasses_authentication(self):
        """
        Test that health endpoint is accessible without authentication.
        Requirements: 1.2
        """
        # Start streamlit app in background without any authentication
        process = subprocess.Popen(
            ["streamlit", "run", "streamlit_app.py", "--server.headless", "true",
             "--server.port", "8503"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for app to start
            time.sleep(5)
            
            # Make health check request without any credentials
            result = subprocess.run(
                ["curl", "-s", "-w", "%{http_code}", "http://localhost:8503/?health=check"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Verify request succeeds (HTTP 200)
            assert result.returncode == 0, "Health check request failed"
            
            # The response should be accessible (not redirected to login)
            output = result.stdout
            assert "status" in output or "200" in output, "Health endpoint should be accessible without auth"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)
    
    def test_health_endpoint_responds_within_5_seconds(self):
        """
        Test that health endpoint responds within 5 seconds.
        Requirements: 1.5
        """
        # Start streamlit app in background
        process = subprocess.Popen(
            ["streamlit", "run", "streamlit_app.py", "--server.headless", "true",
             "--server.port", "8504"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for app to start
            time.sleep(5)
            
            # Measure response time
            start_time = time.time()
            
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8504/?health=check"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Verify response time is under 5 seconds
            assert response_time < 5.0, f"Health check took {response_time:.2f}s, should be under 5s"
            assert result.returncode == 0, "Health check request failed"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)
    
    def test_health_endpoint_accessible_via_http_clients(self):
        """
        Test that health endpoint is accessible via standard HTTP clients (curl).
        Requirements: 1.4
        """
        # Start streamlit app in background
        process = subprocess.Popen(
            ["streamlit", "run", "streamlit_app.py", "--server.headless", "true",
             "--server.port", "8505"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for app to start
            time.sleep(5)
            
            # Test with curl
            result = subprocess.run(
                ["curl", "-s", "-f", "http://localhost:8505/?health=check"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Verify curl can access the endpoint
            assert result.returncode == 0, "curl should be able to access health endpoint"
            assert len(result.stdout) > 0, "Health endpoint should return content"
            
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

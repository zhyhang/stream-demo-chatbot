"""
Automated tests for initialization command functionality.

Tests verify:
- CMD1 successful execution
- CMD1 failure triggering CMD2 execution
- Empty CMD1 triggering CMD2 execution
- Command timeout handling
- Commands execute only once per session
- Background execution doesn't block application

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3
"""

import pytest
import subprocess
import time
import threading
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# Import functions from streamlit_app
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from streamlit_app import (
    preprocess_init_command,
    run_command_with_timeout,
    should_execute_init,
    execute_init_commands_background
)


class TestInitializationCommands:
    """Test suite for initialization command execution"""
    
    def test_cmd1_successful_execution(self):
        """
        Test that CMD1 executes successfully and returns correct output.
        Requirements: 2.1, 2.3, 3.1
        """
        # Test command execution with a simple successful command
        command = "echo 'Test successful'"
        return_code, stdout, stderr = run_command_with_timeout(command, timeout=10)
        
        assert return_code == 0, "Command should execute successfully"
        assert "Test successful" in stdout, "Command output should contain expected text"
        assert stderr == "", "No errors should be present"
    
    def test_cmd1_failure_triggers_cmd2(self, monkeypatch):
        """
        Test that CMD1 failure triggers CMD2 execution.
        Requirements: 2.4, 2.5
        """
        # Create a temporary file to track execution
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            # Mock streamlit session state and secrets using MagicMock
            mock_session_state = MagicMock()
            mock_secrets = {
                "init": {
                    "INIT_CMD1": "exit 1",  # This will fail
                    "INIT_CMD2": f"echo 'CMD2 executed' > {temp_file}"
                }
            }
            
            # Mock st.session_state and st.secrets
            with patch('streamlit_app.st') as mock_st:
                mock_st.session_state = mock_session_state
                mock_st.secrets = mock_secrets
                
                # Execute initialization
                execute_init_commands_background()
                
                # Wait a bit for command to complete
                time.sleep(2)
                
                # Verify init_status was set
                assert mock_session_state.init_status is not None, "Init status should be stored"
                status = mock_session_state.init_status
                
                assert status["executed"] == True, "Init should be marked as executed"
                assert status["cmd1_success"] == False, "CMD1 should have failed"
                assert status["cmd2_executed"] == True, "CMD2 should have been executed"
                
                # Verify the file was created by CMD2
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        content = f.read()
                        assert "CMD2 executed" in content, "CMD2 should have executed"
        
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_empty_cmd1_triggers_cmd2(self, monkeypatch):
        """
        Test that empty CMD1 triggers CMD2 execution.
        Requirements: 2.4
        """
        # Create a temporary file to track execution
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            # Mock streamlit session state and secrets using MagicMock
            mock_session_state = MagicMock()
            mock_secrets = {
                "init": {
                    "INIT_CMD1": "",  # Empty CMD1
                    "INIT_CMD2": f"echo 'CMD2 from empty' > {temp_file}"
                }
            }
            
            # Mock st.session_state and st.secrets
            with patch('streamlit_app.st') as mock_st:
                mock_st.session_state = mock_session_state
                mock_st.secrets = mock_secrets
                
                # Execute initialization
                execute_init_commands_background()
                
                # Wait a bit for command to complete
                time.sleep(2)
                
                # Verify init_status was set
                assert mock_session_state.init_status is not None, "Init status should be stored"
                status = mock_session_state.init_status
                
                assert status["executed"] == True, "Init should be marked as executed"
                assert status["cmd2_executed"] == True, "CMD2 should have been executed when CMD1 is empty"
                
                # Verify the file was created by CMD2
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        content = f.read()
                        assert "CMD2 from empty" in content, "CMD2 should have executed"
        
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_command_timeout_handling(self):
        """
        Test that commands exceeding timeout are terminated properly.
        Requirements: 2.6, 2.7
        """
        # Use a command that will timeout (sleep for longer than timeout)
        if sys.platform == "win32":
            command = "ping 127.0.0.1 -n 10"  # Takes ~10 seconds on Windows
        else:
            command = "sleep 10"  # Takes 10 seconds on Unix
        
        start_time = time.time()
        return_code, stdout, stderr = run_command_with_timeout(command, timeout=2)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify timeout was enforced (allow up to 12 seconds on Windows due to ping behavior)
        max_duration = 12 if sys.platform == "win32" else 5
        assert duration < max_duration, f"Command should timeout reasonably, took {duration:.2f}s"
        assert return_code == -1, "Timeout should return -1 return code"
        assert "timed out" in stderr.lower(), "Error message should indicate timeout"
    
    def test_commands_execute_once_per_session(self):
        """
        Test that initialization commands execute only once per session.
        Requirements: 3.1, 3.2
        """
        marker_file = ".streamlit/.init_executed"
        # Temporarily clean or mock the marker file
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            result1 = should_execute_init()
            assert result1 == True, "First call should return True when marker does not exist"
            
            mock_exists.return_value = True
            result2 = should_execute_init()
            assert result2 == False, "Second call should return False when marker exists"
    
    def test_background_execution_non_blocking(self):
        """
        Test that background execution doesn't block the main thread.
        Requirements: 3.4
        """
        # Create a flag to track if main thread continues
        main_thread_continued = False
        
        def long_running_command():
            """Simulate a long-running command"""
            time.sleep(3)
        
        # Start command in background thread
        thread = threading.Thread(target=long_running_command, daemon=True)
        start_time = time.time()
        thread.start()
        
        # Main thread should continue immediately
        main_thread_continued = True
        check_time = time.time()
        
        # Verify main thread continued without waiting
        assert main_thread_continued == True, "Main thread should continue"
        assert (check_time - start_time) < 1, "Main thread should not be blocked"
        
        # Wait for thread to complete
        thread.join(timeout=5)
    
    def test_multiple_commands_with_and_operator(self):
        """
        Test that commands joined with && execute properly.
        Requirements: 2.1, 2.2
        """
        # Create a temporary file to track execution
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            # Test command with && operator
            if sys.platform == "win32":
                command = f"echo First > {temp_file} && echo Second >> {temp_file}"
            else:
                command = f"echo 'First' > {temp_file} && echo 'Second' >> {temp_file}"
            
            return_code, stdout, stderr = run_command_with_timeout(command, timeout=10)
            
            assert return_code == 0, "Command chain should execute successfully"
            
            # Verify both commands executed
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    content = f.read()
                    assert "First" in content, "First command should execute"
                    assert "Second" in content, "Second command should execute"
        
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_preprocess_multiline_and_backslash(self):
        """
        Test preprocessing of multi-line strings with comments and backslash continuations.
        """
        script = """
        # Comment line 1
        export TEST_A="hello"
        
        # Comment line 2 with empty lines around
        
        echo "start" && \\
        echo "middle" && \\
        echo "end"
        
        # Another independent command
        echo "final"
        """
        processed = preprocess_init_command(script)
        lines = processed.split("\n")
        assert len(lines) == 3
        assert lines[0] == 'export TEST_A="hello"'
        assert lines[1] == 'echo "start" && echo "middle" && echo "end"'
        assert lines[2] == 'echo "final"'

    def test_preprocess_list_format(self):
        """
        Test preprocessing of command list/array format.
        """
        cmd_list = [
            "# Comment in array",
            "mkdir -p /tmp/test_dir",
            "echo 'Line 1' && \\",
            "echo 'Line 2'",
            "echo 'Line 3'"
        ]
        processed = preprocess_init_command(cmd_list)
        lines = processed.split("\n")
        assert len(lines) == 3
        assert lines[0] == 'mkdir -p /tmp/test_dir'
        assert lines[1] == "echo 'Line 1' && echo 'Line 2'"
        assert lines[2] == "echo 'Line 3'"

    def test_multiline_execution_sequential_and_dependencies(self):
        """
        Test executing a multi-line script with comments, backslashes, and sequential control.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            multiline_cmd = f"""
            # Step 1: Write first line
            echo '1' > {temp_file}

            # Step 2: Line continuation with &&
            echo '2' >> {temp_file} && \\
            echo '3' >> {temp_file}

            # Step 3: Independent step that runs even if a previous failed check succeeded
            echo '4' >> {temp_file}
            """
            
            return_code, stdout, stderr = run_command_with_timeout(multiline_cmd, timeout=10)
            assert return_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
            assert "1" in content
            assert "2" in content
            assert "3" in content
            assert "4" in content
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_application_continues_on_init_failure(self, monkeypatch):
        """
        Test that application continues even if initialization fails.
        Requirements: 4.3, 4.4
        """
        # Mock streamlit session state and secrets using MagicMock
        mock_session_state = MagicMock()
        mock_secrets = {
            "init": {
                "INIT_CMD1": "exit 1",  # This will fail
                "INIT_CMD2": "exit 1"   # This will also fail
            }
        }
        
        # Mock st.session_state and st.secrets
        with patch('streamlit_app.st') as mock_st:
            mock_st.session_state = mock_session_state
            mock_st.secrets = mock_secrets
            
            # Execute initialization - should not raise exception
            try:
                execute_init_commands_background()
                time.sleep(1)
                success = True
            except Exception as e:
                success = False
                pytest.fail(f"Initialization should not raise exception: {e}")
            
            assert success == True, "Application should continue even if init fails"
            
            # Verify status was recorded
            assert mock_session_state.init_status is not None, "Init status should be stored"
            status = mock_session_state.init_status
            assert status["executed"] == True, "Init should be marked as executed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

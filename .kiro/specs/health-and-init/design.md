# Design Document

## Overview

This design document outlines the implementation approach for adding a public health check endpoint and startup initialization command execution to the Streamlit application. The solution leverages Streamlit's query parameters for the health endpoint and Python's threading/subprocess modules for background command execution.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Application                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────┐         ┌──────────────────────┐   │
│  │  Health Check  │         │  Initialization      │   │
│  │  Handler       │         │  Manager             │   │
│  │                │         │                      │   │
│  │  - Check query │         │  - Execute INIT_CMD1 │   │
│  │    params      │         │  - Fallback to CMD2  │   │
│  │  - Return JSON │         │  - Background exec   │   │
│  └────────────────┘         │  - 5min timeout      │   │
│                              └──────────────────────┘   │
│                                       │                  │
│  ┌────────────────────────────────────┼────────────┐   │
│  │         Main Application           │            │   │
│  │  - Login/Auth                      │            │   │
│  │  - Chatbot                         │            │   │
│  │  - Command Executor                │            │   │
│  └────────────────────────────────────┘            │   │
│                                                     │   │
└─────────────────────────────────────────────────────┼───┘
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                            │  System Shell    │
                                            │  (subprocess)    │
                                            └──────────────────┘
```

### Component Interaction Flow

```
Application Startup
    │
    ├─→ Check query params
    │   └─→ If ?health=check → Return health status (bypass auth)
    │
    ├─→ Initialize session state
    │   └─→ Check if init_executed flag exists
    │       └─→ If not executed:
    │           ├─→ Read INIT_CMD1 from secrets
    │           ├─→ Execute in background thread
    │           ├─→ Monitor with 5min timeout
    │           └─→ If fails → Execute INIT_CMD2
    │
    ├─→ Check login status
    │   ├─→ If not logged in → Show login form
    │   └─→ If logged in → Show main app
    │
    └─→ Continue normal app flow

Note: Initialization commands execute BEFORE login check, ensuring
they run regardless of authentication status.
```

## Components and Interfaces

### 1. Health Check Handler

**Purpose**: Provide a public endpoint for health status checks

**Implementation Approach**:
- Use Streamlit's `st.query_params` to detect health check requests
- Check for query parameter: `?health=check`
- Return minimal JSON-like response before authentication
- Use `st.json()` or `st.write()` to display response
- Use `st.stop()` to prevent further execution

**Interface**:
```python
def check_health_endpoint() -> bool:
    """
    Check if the current request is a health check.
    Returns True if health endpoint was triggered (and handled).
    """
    pass

def render_health_response() -> None:
    """
    Render the health check response and stop execution.
    """
    pass
```

**Response Format**:
```json
{
    "status": "healthy",
    "timestamp": "2025-11-10T12:00:00Z"
}
```

### 2. Initialization Command Manager

**Purpose**: Execute configured initialization commands on first startup

**Implementation Approach**:
- Use `st.session_state` to track execution status
- Read INIT_CMD1 and INIT_CMD2 from `st.secrets`
- Use Python's `threading` module for background execution
- Use `subprocess.run()` with timeout parameter (300 seconds)
- Implement fallback logic: CMD1 → (if fails) → CMD2
- Log all execution details to console

**Interface**:
```python
def execute_init_commands() -> None:
    """
    Execute initialization commands if not already executed.
    Runs in background thread with timeout and fallback logic.
    """
    pass

def run_command_with_timeout(command: str, timeout: int = 300) -> tuple[int, str, str]:
    """
    Execute a shell command with timeout.
    Returns: (return_code, stdout, stderr)
    """
    pass

def should_execute_init() -> bool:
    """
    Check if initialization commands should be executed.
    """
    pass
```

**State Management**:
```python
# Session state keys
st.session_state.init_executed: bool  # Tracks if init ran
st.session_state.init_status: dict    # Stores execution results
```

### 3. Integration with Existing Application

**Modification Points**:
1. **Application Entry Point** (`if __name__ == "__main__"`):
   - Add health check handler at the very beginning (before any other logic)
   - Add initialization command execution immediately after health check
   - Ensure init commands execute BEFORE the login check
   - This guarantees initialization runs regardless of authentication state

2. **Secrets Configuration** (`.streamlit/secrets.toml`):
   - Add new optional fields: `INIT_CMD1` and `INIT_CMD2`

**Execution Order (Critical)**:
```
1. Health check (if requested)
2. Initialization commands (once per session)
3. Login check
4. Main application
```

## Data Models

### Health Check Response
```python
{
    "status": str,      # "healthy" or "ok"
    "timestamp": str    # ISO 8601 format timestamp
}
```

### Initialization Status
```python
{
    "executed": bool,           # Whether init was attempted
    "cmd1_success": bool,       # CMD1 execution result
    "cmd2_executed": bool,      # Whether CMD2 was needed
    "cmd2_success": bool,       # CMD2 execution result (if executed)
    "logs": list[str]          # Execution logs
}
```

### Secrets Configuration Schema
```toml
[login]
username = "user"
password = "pass"

[init]
INIT_CMD1 = "command1 && command2 && command3"  # Optional
INIT_CMD2 = "fallback_command"                   # Optional
```

## Error Handling

### Health Check Endpoint
- **No errors expected**: Simple query parameter check and JSON response
- **Fallback**: If any error occurs, allow normal app flow to continue

### Initialization Commands

**Timeout Handling**:
```python
try:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes
    )
except subprocess.TimeoutExpired:
    # Log timeout and proceed to CMD2 if available
    log_error("Command timed out after 5 minutes")
```

**Execution Failure Handling**:
```python
if return_code != 0:
    # Log failure
    log_error(f"Command failed with return code {return_code}")
    # Attempt CMD2 if available
    if INIT_CMD2:
        execute_cmd2()
```

**Missing Configuration**:
- If neither INIT_CMD1 nor INIT_CMD2 is configured, skip initialization silently
- Log informational message: "No initialization commands configured"

**Application Continuity**:
- Initialization failures SHALL NOT prevent application startup
- All errors are logged but application continues normal operation
- Users can still access the application even if init commands fail

## Testing Strategy

### Health Check Endpoint Testing

**Manual Testing**:
```bash
# Test health endpoint
curl http://localhost:8501/?health=check

# Expected response:
# {"status": "healthy", "timestamp": "2025-11-10T12:00:00Z"}
```

**Test Cases**:
1. Health endpoint returns 200 status
2. Health endpoint bypasses authentication
3. Response contains required fields
4. Normal application flow works without health parameter

### Initialization Commands Testing

**Test Scenarios**:

1. **CMD1 Success**:
   - Configure INIT_CMD1 with valid command
   - Verify execution on first startup
   - Verify no re-execution on page refresh

2. **CMD1 Failure → CMD2 Execution**:
   - Configure INIT_CMD1 with failing command (e.g., `exit 1`)
   - Configure INIT_CMD2 with valid command
   - Verify CMD2 executes after CMD1 fails

3. **CMD1 Empty → CMD2 Execution**:
   - Leave INIT_CMD1 empty or unconfigured
   - Configure INIT_CMD2 with valid command
   - Verify CMD2 executes

4. **Timeout Handling**:
   - Configure INIT_CMD1 with long-running command (e.g., `sleep 400`)
   - Verify timeout after 5 minutes
   - Verify CMD2 executes after timeout

5. **Background Execution**:
   - Configure INIT_CMD1 with command that takes 10 seconds
   - Verify application UI loads immediately
   - Verify command completes in background

6. **Execution Before Login**:
   - Configure INIT_CMD1 with command that creates a test file
   - Start application without logging in
   - Verify command executed and file exists
   - Verify login form is displayed after init completes

**Test Commands**:
```toml
# Success test
INIT_CMD1 = "echo 'Init started' && sleep 2 && echo 'Init completed'"

# Failure test
INIT_CMD1 = "exit 1"
INIT_CMD2 = "echo 'Fallback executed'"

# Timeout test
INIT_CMD1 = "sleep 400"
INIT_CMD2 = "echo 'Timeout fallback'"
```

### Integration Testing

1. Verify health endpoint works with running application
2. Verify initialization commands execute before user login
3. Verify application functions normally after init commands
4. Verify logs contain init command output

## Implementation Notes

### Streamlit-Specific Considerations

**Query Parameters**:
- Streamlit provides `st.query_params` (or `st.experimental_get_query_params()` in older versions)
- Must check query params at the very beginning of the script

**Session State**:
- Session state persists across reruns within the same session
- Perfect for tracking init execution status
- Resets when user refreshes browser (new session)

**Background Execution**:
- Streamlit reruns the entire script on interaction
- Use threading to prevent blocking the UI
- Store thread reference to avoid duplicate executions

**Script Execution Flow**:
```python
# Top of script - runs on every rerun
if check_health_endpoint():
    render_health_response()
    st.stop()  # Prevent further execution

# Init commands - run once per session BEFORE login
# This ensures initialization happens regardless of authentication
if should_execute_init():
    execute_init_commands()

# Normal app flow - login check happens AFTER init
if not check_login():
    login_form()
else:
    main_app()
```

### Security Considerations

1. **Health Endpoint**: Public by design, returns minimal information
2. **Init Commands**: Executed with same privileges as application
3. **Command Injection**: Commands come from secrets.toml (trusted source)
4. **Logging**: Avoid logging sensitive information from command output

### Performance Considerations

1. **Background Execution**: Init commands don't block UI rendering
2. **Timeout**: 5-minute limit prevents indefinite hanging
3. **Health Check**: Minimal overhead, returns immediately
4. **Session State**: Efficient in-memory storage for execution tracking

## Design Decisions and Rationales

### Decision 1: Use Query Parameters for Health Check
**Rationale**: Streamlit doesn't support custom HTTP endpoints, but query parameters provide a simple way to detect health check requests before authentication.

**Alternatives Considered**:
- Custom Flask/FastAPI wrapper: Too complex, requires significant refactoring
- Separate health check service: Adds deployment complexity

### Decision 2: Threading for Background Execution
**Rationale**: Python's threading module is simple and sufficient for running shell commands without blocking the UI.

**Alternatives Considered**:
- asyncio: More complex, Streamlit isn't fully async-compatible
- multiprocessing: Overkill for simple command execution

### Decision 3: Session State for Execution Tracking
**Rationale**: Session state is the standard Streamlit mechanism for maintaining state across reruns within a session.

**Alternatives Considered**:
- File-based persistence: Would persist across sessions (not desired)
- Database: Too complex for simple boolean flag

### Decision 4: 5-Minute Timeout
**Rationale**: Balances allowing sufficient time for complex initialization tasks while preventing indefinite hangs.

**Alternatives Considered**:
- No timeout: Risk of hanging indefinitely
- Shorter timeout (1-2 min): May not be sufficient for complex setups
- Configurable timeout: Adds complexity without clear benefit

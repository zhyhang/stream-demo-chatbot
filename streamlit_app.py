import streamlit as st
from openai import OpenAI
import subprocess
import os
import threading
from datetime import datetime, timezone

# Initialization command execution functions
def preprocess_init_command(command):
    """
    Preprocess initialization commands from secrets.
    
    Supports:
    - Lists/tuples of strings (e.g. TOML array of commands)
    - Multi-line strings with comments (#) and blank lines
    - Backslash line continuations (\\)
    - Normalizes CRLF to LF
    - Sequential execution of separate lines
    
    Args:
        command: String or list/tuple of command strings
        
    Returns:
        str: Cleaned, executable script string
    """
    if command is None:
        return ""
        
    if isinstance(command, (list, tuple)):
        lines = [str(line) for line in command]
    elif isinstance(command, str):
        lines = command.replace("\r\n", "\n").split("\n")
    else:
        lines = [str(command)]
        
    processed_lines = []
    current_line = ""
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines or pure comment lines when not continuing a previous line
        if not current_line and (not stripped or stripped.startswith("#")):
            continue
            
        # Handle line continuation with trailing backslash
        if stripped.endswith("\\"):
            part = stripped[:-1].rstrip()
            if part:
                if current_line:
                    current_line += " " + part
                else:
                    current_line = part
        else:
            if current_line:
                current_line += " " + stripped
                processed_lines.append(current_line)
                current_line = ""
            else:
                if stripped and not stripped.startswith("#"):
                    processed_lines.append(stripped)
                    
    if current_line:
        processed_lines.append(current_line)
        
    return "\n".join(processed_lines)

def run_command_with_timeout(command, timeout=300):
    """
    Execute a shell command with timeout.
    
    Args:
        command: Shell command string or list/tuple of commands
        timeout: Maximum execution time in seconds (default: 300 = 5 minutes)
    
    Returns:
        tuple: (return_code, stdout, stderr)
    """
    cmd_str = preprocess_init_command(command)
    if not cmd_str.strip():
        return (0, "", "")

    start_time = datetime.now(timezone.utc)
    print(f"[INIT] [{start_time.isoformat()}] Starting command execution (timeout: {timeout}s)")
    
    # Choose bash if available on Unix/Linux, fallback to default shell
    executable = "/bin/bash" if (os.name != "nt" and os.path.exists("/bin/bash")) else None
    
    try:
        result = subprocess.run(
            cmd_str,
            shell=True,
            executable=executable,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        print(f"[INIT] [{end_time.isoformat()}] Command completed in {duration:.2f}s with return code {result.returncode}")
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        end_time = datetime.now(timezone.utc)
        print(f"[INIT] [{end_time.isoformat()}] ERROR: Command timed out after {timeout} seconds")
        return (-1, "", f"Command timed out after {timeout} seconds")
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        print(f"[INIT] [{end_time.isoformat()}] ERROR: Exception during command execution: {str(e)}")
        return (-1, "", f"Error executing command: {str(e)}")

def should_execute_init():
    """
    Check if initialization commands should be executed.
    Uses a file marker to persist state across app restarts and page refreshes.
    
    Returns:
        bool: True if initialization should run, False otherwise
    """
    # Use a file marker to track if initialization has been executed
    marker_file = ".streamlit/.init_executed"
    return not os.path.exists(marker_file)

def execute_init_commands_background():
    """
    Execute initialization commands in background thread.
    This function runs the actual command execution logic.
    """
    init_start_time = datetime.now(timezone.utc)
    print(f"[INIT] ========================================")
    print(f"[INIT] [{init_start_time.isoformat()}] Initialization sequence started")
    print(f"[INIT] ========================================")
    
    try:
        # Initialize status tracking
        status = {
            "executed": True,
            "cmd1_success": False,
            "cmd2_executed": False,
            "cmd2_success": False,
            "logs": []
        }
        
        # Read commands from secrets
        init_cmd1 = st.secrets.get("init", {}).get("INIT_CMD1", "")
        init_cmd2 = st.secrets.get("init", {}).get("INIT_CMD2", "")
        
        # Log configuration
        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Reading initialization configuration from secrets")
        
        preprocessed_cmd1 = preprocess_init_command(init_cmd1)
        preprocessed_cmd2 = preprocess_init_command(init_cmd2)
        
        if preprocessed_cmd1:
            first_line = preprocessed_cmd1.split("\n")[0]
            print(f"[INIT] INIT_CMD1 configured ({len(preprocessed_cmd1.splitlines())} lines): {first_line[:50]}{'...' if len(first_line) > 50 else ''}")
            status["logs"].append(f"INIT_CMD1 configured: {first_line}")
        else:
            print(f"[INIT] INIT_CMD1 not configured or empty")
            
        if preprocessed_cmd2:
            first_line2 = preprocessed_cmd2.split("\n")[0]
            print(f"[INIT] INIT_CMD2 configured ({len(preprocessed_cmd2.splitlines())} lines): {first_line2[:50]}{'...' if len(first_line2) > 50 else ''}")
            status["logs"].append(f"INIT_CMD2 configured: {first_line2}")
        else:
            print(f"[INIT] INIT_CMD2 not configured or empty")
        
        # Execute CMD1 if configured and not empty
        if preprocessed_cmd1:
            print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Starting INIT_CMD1 execution")
            status["logs"].append(f"Executing INIT_CMD1:\n{preprocessed_cmd1}")
            
            return_code, stdout, stderr = run_command_with_timeout(preprocessed_cmd1, timeout=300)
            
            if return_code == 0:
                status["cmd1_success"] = True
                print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] SUCCESS: INIT_CMD1 completed successfully")
                status["logs"].append("INIT_CMD1 completed successfully")
                if stdout:
                    print(f"[INIT] INIT_CMD1 stdout:\n{stdout}")
                    status["logs"].append(f"stdout: {stdout}")
            else:
                print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] FAILURE: INIT_CMD1 failed with return code {return_code}")
                status["logs"].append(f"INIT_CMD1 failed with return code {return_code}")
                if stderr:
                    print(f"[INIT] INIT_CMD1 stderr:\n{stderr}")
                    status["logs"].append(f"stderr: {stderr}")
                
                # Execute CMD2 as fallback
                if preprocessed_cmd2:
                    print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Starting INIT_CMD2 execution (fallback after CMD1 failure)")
                    status["cmd2_executed"] = True
                    status["logs"].append(f"Executing INIT_CMD2 (fallback):\n{preprocessed_cmd2}")
                    
                    return_code2, stdout2, stderr2 = run_command_with_timeout(preprocessed_cmd2, timeout=300)
                    
                    if return_code2 == 0:
                        status["cmd2_success"] = True
                        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] SUCCESS: INIT_CMD2 completed successfully")
                        status["logs"].append("INIT_CMD2 completed successfully")
                        if stdout2:
                            print(f"[INIT] INIT_CMD2 stdout:\n{stdout2}")
                            status["logs"].append(f"stdout: {stdout2}")
                    else:
                        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] FAILURE: INIT_CMD2 failed with return code {return_code2}")
                        status["logs"].append(f"INIT_CMD2 failed with return code {return_code2}")
                        if stderr2:
                            print(f"[INIT] INIT_CMD2 stderr:\n{stderr2}")
                            status["logs"].append(f"stderr: {stderr2}")
                else:
                    print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] WARNING: No INIT_CMD2 configured for fallback")
        
        # If CMD1 is empty or not configured, execute CMD2
        elif preprocessed_cmd2:
            print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] INIT_CMD1 empty or not configured, starting INIT_CMD2 execution")
            status["cmd2_executed"] = True
            status["logs"].append(f"Executing INIT_CMD2 (CMD1 empty):\n{preprocessed_cmd2}")
            
            return_code, stdout, stderr = run_command_with_timeout(preprocessed_cmd2, timeout=300)
            
            if return_code == 0:
                status["cmd2_success"] = True
                print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] SUCCESS: INIT_CMD2 completed successfully")
                status["logs"].append("INIT_CMD2 completed successfully")
                if stdout:
                    print(f"[INIT] INIT_CMD2 stdout:\n{stdout}")
                    status["logs"].append(f"stdout: {stdout}")
            else:
                print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] FAILURE: INIT_CMD2 failed with return code {return_code}")
                status["logs"].append(f"INIT_CMD2 failed with return code {return_code}")
                if stderr:
                    print(f"[INIT] INIT_CMD2 stderr:\n{stderr}")
                    status["logs"].append(f"stderr: {stderr}")
        else:
            print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] INFO: No initialization commands configured")
            status["logs"].append("No initialization commands configured")
        
        # Store status in session state
        st.session_state.init_status = status
        
        init_end_time = datetime.now(timezone.utc)
        total_duration = (init_end_time - init_start_time).total_seconds()
        print(f"[INIT] ========================================")
        print(f"[INIT] [{init_end_time.isoformat()}] Initialization sequence completed")
        print(f"[INIT] Total duration: {total_duration:.2f}s")
        print(f"[INIT] CMD1 Success: {status['cmd1_success']}, CMD2 Executed: {status['cmd2_executed']}, CMD2 Success: {status['cmd2_success']}")
        print(f"[INIT] ========================================")
        
    except Exception as e:
        error_time = datetime.now(timezone.utc)
        print(f"[INIT] ========================================")
        print(f"[INIT] [{error_time.isoformat()}] CRITICAL ERROR during initialization: {str(e)}")
        print(f"[INIT] ========================================")
        st.session_state.init_status = {
            "executed": True,
            "cmd1_success": False,
            "cmd2_executed": False,
            "cmd2_success": False,
            "logs": [f"Error during initialization: {str(e)}"]
        }

def execute_init_commands():
    """
    Execute initialization commands if not already executed.
    Runs in background thread with timeout and fallback logic.
    Uses a file marker to persist state across app restarts and page refreshes.
    """
    if should_execute_init():
        # Create marker file immediately to prevent duplicate execution
        marker_file = ".streamlit/.init_executed"
        try:
            os.makedirs(os.path.dirname(marker_file), exist_ok=True)
            with open(marker_file, 'w') as f:
                f.write(f"Initialization executed at {datetime.now(timezone.utc).isoformat()}\n")
            print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Created initialization marker file: {marker_file}")
        except Exception as e:
            print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] WARNING: Failed to create marker file: {str(e)}")
        
        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Starting initialization thread (background execution)")
        
        # Start background thread for command execution
        thread = threading.Thread(target=execute_init_commands_background, daemon=True)
        thread.start()
        
        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Initialization thread started successfully")
    else:
        print(f"[INIT] [{datetime.now(timezone.utc).isoformat()}] Initialization already executed, skipping")

# Health check endpoint handler
def check_health_endpoint():
    """
    Check if the current request is a health check.
    Returns True if health endpoint was triggered (and handled).
    """
    try:
        # Get query parameters
        query_params = st.query_params
        
        # Check if health=check parameter is present
        if query_params.get("health") == "check":
            # Log health check request (optional logging)
            print(f"[HEALTH] [{datetime.now(timezone.utc).isoformat()}] Health check request received")
            return True
    except Exception as e:
        # If there's any error accessing query params, continue normal flow
        print(f"[HEALTH] [{datetime.now(timezone.utc).isoformat()}] ERROR: Failed to check query parameters: {str(e)}")
        pass
    
    return False

def render_health_response():
    """
    Render the health check response and stop execution.
    """
    request_time = datetime.now(timezone.utc)
    
    # Create health response with status and timestamp
    health_response = {
        "status": "healthy",
        "timestamp": request_time.isoformat()
    }
    
    # Log the response (optional logging)
    print(f"[HEALTH] [{request_time.isoformat()}] Returning health check response: {health_response}")
    
    # Display the JSON response
    st.json(health_response)
    
    # Log completion
    print(f"[HEALTH] [{datetime.now(timezone.utc).isoformat()}] Health check request completed successfully")
    
    # Stop further execution
    st.stop()

# 登录功能
def check_login():
    """检查用户是否已登录"""
    return st.session_state.get("logged_in", False)

def login_form():
    """显示登录表单"""
    st.title("🔐 登录")
    st.write("请输入用户名和密码来访问聊天机器人")
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submit_button = st.form_submit_button("登录")
        
        if submit_button:
            # 从secrets中获取正确的用户名和密码
            correct_username = st.secrets["login"]["username"]
            correct_password = st.secrets["login"]["password"]
            
            if username == correct_username and password == correct_password:
                st.session_state.logged_in = True
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误")

def logout():
    """登出功能"""
    st.session_state.logged_in = False
    st.session_state.messages = []  # 清除聊天记录
    st.rerun()

def execute_command(command):
    """执行Linux命令并返回结果"""
    try:
        # 使用subprocess执行命令
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30  # 30秒超时
        )
        
        # 组合输出和错误信息
        output = ""
        if result.stdout:
            output += f"输出:\n{result.stdout}\n"
        if result.stderr:
            output += f"错误:\n{result.stderr}\n"
        if not output:
            output = "命令执行完成，无输出内容"
            
        output += f"\n返回码: {result.returncode}"
        return output
        
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时 (30秒)"
    except Exception as e:
        return f"错误: {str(e)}"

# 主应用逻辑
def main_app():
    # 在侧边栏添加登出按钮
    with st.sidebar:
        st.write(f"欢迎，{st.secrets['login']['username']}！")
        if st.button("登出"):
            logout()
    
    # Show title and description.
    st.title("💬 Chatbot")
    st.write(
        "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
        "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
        "You can also learn how to build this app step by step by [following our tutorial](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)."
    )

    # Ask user for their OpenAI API key via `st.text_input`.
    # Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
    # via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    else:

        # Create an OpenAI client.
        client = OpenAI(api_key=openai_api_key)

        # Create a session state variable to store the chat messages. This ensures that the
        # messages persist across reruns.
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display the existing chat messages via `st.chat_message`.
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Create a chat input field to allow the user to enter a message. This will display
        # automatically at the bottom of the page.
        if prompt := st.chat_input("What is up?"):

            # Store and display the current prompt.
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate a response using the OpenAI API.
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )

            # Stream the response to the chat using `st.write_stream`, then store it in 
            # session state.
            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Linux命令执行区域
    st.markdown("---")
    st.subheader("🖥️ Linux 命令执行器")
    st.write("在下方输入Linux命令并执行（请谨慎使用，某些命令可能会影响系统）")
    
    # 创建命令输入和执行区域
    col1, col2 = st.columns([4, 1])
    
    with col1:
        command = st.text_input(
            "输入Linux命令:", 
            placeholder="例如: ls -la, pwd, whoami, df -h",
            key="linux_command"
        )
    
    with col2:
        st.write("")  # 添加一些空白以对齐按钮
        execute_btn = st.button("执行", type="primary")
    
    # 执行命令
    if execute_btn and command:
        with st.spinner("正在执行命令..."):
            result = execute_command(command)
        
        st.subheader("执行结果:")
        st.code(result, language="bash")
        
        # 将命令和结果保存到session state中以便查看历史
        if "command_history" not in st.session_state:
            st.session_state.command_history = []
        
        st.session_state.command_history.append({
            "command": command,
            "result": result
        })
    
    elif execute_btn and not command:
        st.warning("请输入要执行的命令")
    
    # 显示命令历史
    if "command_history" in st.session_state and st.session_state.command_history:
        with st.expander("📜 命令历史记录"):
            for i, item in enumerate(reversed(st.session_state.command_history[-5:])):  # 只显示最近5条
                st.write(f"**命令 {len(st.session_state.command_history)-i}:** `{item['command']}`")
                st.code(item['result'], language="bash")
                st.markdown("---")

# 应用入口点
if __name__ == "__main__":
    # Health check endpoint - must be first, before any other logic
    if check_health_endpoint():
        render_health_response()
    
    # Execute initialization commands (once per session, before login check)
    execute_init_commands()
    
    # 检查登录状态
    if not check_login():
        login_form()
    else:
        main_app()

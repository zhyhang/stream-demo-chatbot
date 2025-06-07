import streamlit as st
from openai import OpenAI
import subprocess
import os

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
    # 检查登录状态
    if not check_login():
        login_form()
    else:
        main_app()

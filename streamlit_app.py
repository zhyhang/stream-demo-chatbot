import streamlit as st
from openai import OpenAI

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

# 应用入口点
if __name__ == "__main__":
    # 检查登录状态
    if not check_login():
        login_form()
    else:
        main_app()

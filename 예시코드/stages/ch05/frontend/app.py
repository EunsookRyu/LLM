# frontend/app.py
# 가이드 참조: chapter5_streamlit.md L30–L81
import streamlit as st
import requests
import json
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="내부 문서 AI 챗봇", page_icon="🤖")
st.title("내부 문서 AI 챗봇")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json={
                "model": "default",
                "messages": st.session_state.messages,
                "stream": True
            },
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        full_response += delta["content"]
                        placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

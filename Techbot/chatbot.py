import streamlit as st
from datetime import datetime
from openai import OpenAI
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Setup Groq Client ---
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# --- Page Config ---
st.set_page_config(page_title="🤖 TechBot", page_icon="💬", layout="wide")
st.title("🤖 TechBot - Ask Me Anything Tech!")

# --- Session Initialization ---
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.current_chat_id = new_id
    st.session_state.chat_sessions[new_id] = {
        "messages": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": "new chat"
    }

# --- Helpers ---
def generate_topic_from_messages(messages):
    try:
        prompt = "Generate a short topic heading (3-7 lowercase words, no grammar) based on this conversation:\n"
        chat_summary = "\n".join([msg['content'] for msg in messages if msg['role'] == 'user'])
        topic_response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": chat_summary[:1000]}  # Limit to 1000 chars
            ]
        )
        topic = topic_response.choices[0].message.content.strip().lower()
        return topic
    except Exception as e:
        return "unknown topic"

# --- Sidebar: Chat History ---
with st.sidebar:
    st.header("📁 Chat Topics")
    for chat_id, chat_data in st.session_state.chat_sessions.items():
        if chat_data["topic"] != "new chat":
            label = f"🕓 {chat_data['created_at']}\n🔹 {chat_data['topic']}"
            if st.button(label, key=chat_id):
                st.session_state.current_chat_id = chat_id
                st.rerun()

    st.divider()

    if st.button("🆕 New Chat"):
        current_id = st.session_state.current_chat_id
        current_data = st.session_state.chat_sessions[current_id]
        if current_data["topic"] == "new chat" and current_data["messages"]:
            current_data["topic"] = generate_topic_from_messages(current_data["messages"])

        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        st.session_state.chat_sessions[new_id] = {
            "messages": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topic": "new chat"
        }
        st.rerun()

    if st.button("🗑️ Clear Current Chat"):
        current_id = st.session_state.current_chat_id
        st.session_state.chat_sessions[current_id]["messages"] = []
        st.rerun()

# --- Display Messages ---
current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(f"{msg['content']}\n\n*🕒 {msg['time']}*")

# --- Chat Input ---
user_input = st.chat_input("Ask your tech question here...")
if user_input:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_chat["messages"].append({
        "role": "user",
        "content": user_input,
        "time": now
    })

    with st.chat_message("user"):
        st.markdown(f"{user_input}\n\n*🕒 {now}*")

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # STEP 1: Classify if the question is technical
                check_response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a classifier. Only answer with 'yes' or 'no'. Is this question about technology, software, hardware, programming, computers, technical concepts, mathematics, or logical reasoning?"
                        },
                        {"role": "user", "content": user_input}
                    ]
                )
                is_tech = check_response.choices[0].message.content.strip().lower()

                # STEP 2: If technical, generate a full reply
                if is_tech.startswith("yes"):
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": m["role"], "content": m["content"]} for m in current_chat["messages"]]
                    )
                    reply = response.choices[0].message.content
                else:
                    reply = (
                        "❗ I only answer *technical* questions.\n\n"
                        "Try asking me about programming, software development, hardware, AI, cloud, data, or other tech-related topics."
                    )

                reply_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.markdown(f"{reply}\n\n*🕒 {reply_time}*")

                current_chat["messages"].append({
                    "role": "assistant",
                    "content": reply,
                    "time": reply_time
                })

            except Exception as e:
                st.error("Something went wrong. Please try again later.")

# --- Optional: Auto-generate topic ---
if current_chat["topic"] == "new chat" and len(current_chat["messages"]) >= 2:
    current_chat["topic"] = generate_topic_from_messages(current_chat["messages"])

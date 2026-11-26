"""Everything the UI needs from the backend. Each function maps to one backend route."""
import html
import json
import os
import time
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md"}
MAX_UPLOAD_MB = 20
TYPING = ('<div class="typing"><span></span><span></span><span></span>'
          '<span class="think-label">Thinking…</span></div>')

ss = st.session_state


# ── talking to the backend ─────────────────────────────────────────────────────
def api(method, path, **kwargs):
    """Returns (ok, data). On failure, data is an error message."""
    try:
        r = requests.request(method, API_BASE_URL + path, timeout=300, **kwargs)
    except requests.RequestException:
        ss.server_down = True
        return False, f"Could not reach the server at {API_BASE_URL}."
    if r.ok:
        return True, r.json()
    try:
        return False, str(r.json().get("detail", r.text))
    except ValueError:
        return False, r.text


def server_ok():                                   # GET /health
    try:
        requests.get(API_BASE_URL + "/health", timeout=3).raise_for_status()
        ss.server_down = False
        return True
    except requests.RequestException:
        ss.server_down = True
        return False


# ── session state ──────────────────────────────────────────────────────────────
def init_state():
    defaults = dict(
        theme="Dark", font_size="Default", compact=False, show_sources=True, language="English",
        sidebar_open=True, search="", user={"username": "Guest"},
        chats=None, current_chat_id=None, messages=[], pending=False,
        docs=[], upload_nonce=0, server_down=False,
    )
    for key, value in defaults.items():
        ss.setdefault(key, value)


def toggle_sidebar():
    ss.sidebar_open = not ss.sidebar_open


def request_settings():
    ss.open_settings = True


def request_regen():
    ss.regen = True


# ── chats ──────────────────────────────────────────────────────────────────────
def load_chat_history():                           # GET /chats
    ok, data = api("GET", "/chats")
    ss.chats = data if ok else []


def new_chat():
    ss.current_chat_id = None
    ss.messages = []
    ss.pending = False
    st.query_params.clear()


def open_chat(chat_id):                            # GET /chats/{id}
    ss.pending = False
    ok, data = api("GET", f"/chats/{chat_id}")
    if not ok:
        new_chat()
        return
    ss.current_chat_id = chat_id
    ss.messages = data["messages"]
    st.query_params["chat"] = str(chat_id)


def restore_chat_from_url():
    """Reopen the chat from ?chat=<id> after a browser refresh."""
    if ss.get("url_checked"):
        return
    ss.url_checked = True
    chat_id = st.query_params.get("chat")
    if chat_id and str(chat_id).isdigit():
        open_chat(int(chat_id))


def rename_chat(chat_id, input_key):               # PATCH /chats/{id}
    title = (ss.get(input_key) or "").strip()
    if title:
        api("PATCH", f"/chats/{chat_id}", json={"title": title})
        load_chat_history()


def ask_delete(chat_id):
    ss.confirm_delete = chat_id


def delete_chat(chat_id):                          # DELETE /chats/{id}
    api("DELETE", f"/chats/{chat_id}")
    if ss.current_chat_id == chat_id:
        new_chat()
    load_chat_history()


def group_chats(chats, query=""):
    """Filter by search text and group into Today / Yesterday / Previous 7 Days / Older."""
    query = (query or "").strip().lower()
    today = datetime.now().date()
    groups = {"Today": [], "Yesterday": [], "Previous 7 Days": [], "Older": []}
    for chat in chats or []:
        if query and query not in chat["title"].lower():
            continue
        days = (today - datetime.fromisoformat(chat["updated_at"]).date()).days
        label = ("Today" if days <= 0 else "Yesterday" if days == 1
                 else "Previous 7 Days" if days <= 7 else "Older")
        groups[label].append(chat)
    return [(label, items) for label, items in groups.items() if items]


# ── documents ──────────────────────────────────────────────────────────────────
def load_documents():                              # GET /documents
    ok, data = api("GET", "/documents")
    ss.docs = data if ok else []


def upload_to_library(file):                       # POST /upload
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        return False, f"File is larger than {MAX_UPLOAD_MB} MB."
    ok, data = api("POST", "/upload", files={"file": (file.name, file.getvalue())})
    if ok:
        return True, f"Indexed {data['chunks']} chunks."
    return False, data


def _size(n):
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def render_doc_row(doc):
    c_name, c_del = st.columns([6, 1], vertical_alignment="center")
    c_name.markdown(f"📄 **{doc['name']}**")
    c_name.caption(_size(doc["size"]))
    if c_del.button("", icon=":material/delete:", key=f"deldoc_{doc['name']}", help="Delete"):
        api("DELETE", f"/documents/{doc['name']}")   # DELETE /documents/{name}
        st.rerun(scope="fragment")


# ── messages ───────────────────────────────────────────────────────────────────
def _copy_button(text):
    safe = json.dumps(text).replace("</", "<\\/")
    components.html(f"""<style>body{{margin:0}}
button{{width:34px;height:34px;background:transparent;border:1px solid transparent;border-radius:9px;
color:#c8cdd5;cursor:pointer;font-size:16px}}button:hover{{background:#3a404a;color:#fff}}</style>
<button id="b" title="Copy">⧉</button>
<script>
const text = {safe};
const b = document.getElementById('b');
b.onclick = async () => {{
  try {{ await navigator.clipboard.writeText(text); }}
  catch (e) {{ const t = document.createElement('textarea'); t.value = text;
               document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); }}
  b.textContent = '✓'; setTimeout(() => b.textContent = '⧉', 1200);
}};
</script>""", height=36, width=36)


def _render_user(i, msg):
    with st.chat_message("user"):
        with st.container(key=f"umsg_{i}"):
            if msg.get("file"):
                st.markdown(f'<span class="chip">📎 {html.escape(msg["file"])}</span>', unsafe_allow_html=True)
            st.markdown(msg["content"])


def _render_assistant(i, msg, is_last):
    with st.chat_message("assistant"):
        st.markdown(msg["content"])
        if ss.show_sources and msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))
        with st.container(key=f"actions_{i}"):
            c_copy, c_regen, _ = st.columns([1, 1, 12])
            with c_copy:
                _copy_button(msg["content"])
            if is_last:
                c_regen.button("", icon=":material/refresh:", key=f"regen_{i}",
                               help="Regenerate response", on_click=request_regen)


def render_messages():
    last = len(ss.messages) - 1
    for i, msg in enumerate(ss.messages):
        if msg["role"] == "user":
            _render_user(i, msg)
        else:
            _render_assistant(i, msg, i == last)


def scroll_to_bottom():
    components.html(f"""<script>/* {time.time()} */
const m = window.parent.document.querySelector('[data-testid="stMain"]');
if (m) m.scrollTo({{top: m.scrollHeight}});
</script>""", height=0)


def send_prompt(text, file=None, append_user=True):   # POST /chat
    attachment = None
    if file is not None:
        with st.spinner("Uploading and indexing…"):
            ok, msg = upload_to_library(file)
        if not ok:
            st.error(msg)
            return
        attachment = file.name
    elif not append_user and ss.messages:               # regenerate: keep the old attachment
        attachment = ss.messages[-1].get("file")

    if append_user:
        ss.messages.append({"role": "user", "content": text, "file": attachment})
        _render_user(len(ss.messages) - 1, ss.messages[-1])

    ss.pending = True                                   # still True if the user hits Stop
    with st.chat_message("assistant"):
        st.markdown(TYPING, unsafe_allow_html=True)
        with st.container(key="stopbar"):
            st.button("Stop", icon=":material/stop_circle:", key="stop_btn")
        ok, data = api("POST", "/chat", json={
            "question": text,
            "chat_id": ss.current_chat_id,
            "language": ss.language,
            "attachment": attachment,
            "regenerate": not append_user,
        })
    ss.pending = False

    if not ok:
        st.error(data)
        return

    ss.current_chat_id = data["chat_id"]
    ss.messages.append({"role": "assistant", "content": data["answer"], "sources": data["sources"]})
    st.query_params["chat"] = str(ss.current_chat_id)
    load_chat_history()
    st.rerun()


def finalize_interrupted():
    """If a request was cut off (Stop button), leave a note instead of a dangling question."""
    if ss.pending:
        ss.pending = False
        ss.messages.append({"role": "assistant", "content": "_Generation stopped._"})

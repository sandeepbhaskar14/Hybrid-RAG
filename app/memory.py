# Chats and their messages, saved in a small JSON file so they survive restarts.
import json
import os
from datetime import datetime
from app.config import settings

chats = {}  # chat_id -> {"id", "title", "updated_at", "messages": [...]}


def _save():
    with open(settings.CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)


def _load():
    if os.path.exists(settings.CHATS_FILE):
        with open(settings.CHATS_FILE, encoding="utf-8") as f:
            for key, chat in json.load(f).items():
                chats[int(key)] = chat


_load()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def exists(chat_id):
    return chat_id in chats


def create_chat(title):
    chat_id = max(chats, default=0) + 1
    chats[chat_id] = {"id": chat_id, "title": title, "updated_at": _now(), "messages": []}
    _save()
    return chat_id


def list_chats():
    items = [{"id": c["id"], "title": c["title"], "updated_at": c["updated_at"]}
             for c in chats.values()]
    return sorted(items, key=lambda c: c["updated_at"], reverse=True)


def get_chat(chat_id):
    return chats.get(chat_id)


def rename_chat(chat_id, title):
    chats[chat_id]["title"] = title
    _save()


def delete_chat(chat_id):
    chats.pop(chat_id, None)
    _save()


def add_turn(chat_id, question, answer, sources, attachment=None):
    chat = chats[chat_id]
    chat["messages"].append({"role": "user", "content": question, "file": attachment})
    chat["messages"].append({"role": "assistant", "content": answer, "sources": sources})
    chat["updated_at"] = _now()
    _save()


def drop_last_turn(chat_id, question):
    """Used by 'Regenerate': remove the last turn if it is for this same question."""
    messages = chats[chat_id]["messages"]
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            if messages[i]["content"] == question:
                del messages[i:]
                _save()
            return


def get_history(chat_id):
    last_turns = chats[chat_id]["messages"][-10:]  # 5 turns = 10 messages
    lines = []
    for m in last_turns:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)
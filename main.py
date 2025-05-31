from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import sqlite3
import os

app = FastAPI()

# Serve HTML
app.mount("/static", StaticFiles(directory="static"), name="static")


# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()


def save_message(username, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, content, timestamp) VALUES (?, ?, ?)", (username, content, timestamp))
    conn.commit()
    conn.close()
    return timestamp


def get_last_messages(limit=20):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT username, content, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    messages = list(reversed(c.fetchall()))
    conn.close()
    return messages


# === CONNECTION MANAGER ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def register(self, websocket: WebSocket, username: str):
        self.active_connections[websocket] = username
        await self.broadcast_users()

    async def broadcast_users(self):
        users = ",".join(self.active_connections.values())
        for conn in self.active_connections:
            await conn.send_text(f"__USERS__:{users}")

    async def broadcast(self, message: str):
        for conn in self.active_connections:
            await conn.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def home():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        username = await ws.receive_text()
        await manager.register(ws, username)

        # Send previous messages
        for user, msg, ts in get_last_messages():
            await ws.send_text(f"[{ts}] {user}: {msg}")

        while True:
            data = await ws.receive_text()

            if data.startswith("__TYPING__:"):
                typing_user = data.replace("__TYPING__:", "")
                for conn in manager.active_connections:
                    if conn != ws:
                        await conn.send_text(f"__TYPING__:{typing_user}")
                continue

            if data.startswith("[") and "] " in data:
                username, content = data.split("] ", 1)
                username = username.strip("[]")
                timestamp = save_message(username, content)
                await manager.broadcast(f"[{timestamp}] {username}: {content}")
    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast_users()


# Initialize DB at startup
init_db()

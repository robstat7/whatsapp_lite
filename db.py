from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///chat.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


def save_message(username, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, content, timestamp) VALUES (?, ?, ?)", (username, content, timestamp))
    conn.commit()
    conn.close()


def get_last_messages(limit=20):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT username, content, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return reversed(rows)  # return in chronological order

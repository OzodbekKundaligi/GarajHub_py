"""
Copy of root server.py for web project
"""

# Original server.py content copied from project root

import os
import json
import sqlite3
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# FastAPI
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Telegram bot
try:
    import telebot
    from telebot import types
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    print("WARNING: pyTelegramBotAPI not installed, bot will not work")

# ===== KONFIGURATSIYA =====
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@GarajHub_uz')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
PORT = int(os.getenv('PORT', '8000'))

# ===== DATABASE =====
def get_db_path():
    if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
        return os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'garajhub.db')
    elif 'RAILWAY_STORAGE_DIR' in os.environ:
        return os.path.join(os.environ['RAILWAY_STORAGE_DIR'], 'garajhub.db')
    else:
        return 'garajhub.db'

DB_PATH = get_db_path()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            birth_date TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS startups (
            startup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            logo TEXT,
            group_link TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            results TEXT,
            views INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS startup_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            startup_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(startup_id, user_id)
        )
    ''')
    
    cursor.execute('SELECT * FROM admins WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        import hashlib
        hashed_password = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO admins (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', hashed_password, 'Administrator', 'admin@garajhub.uz', 'superadmin'))
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

# BOT_AVAILABLE and bot remain for compatibility but polling should run from bot project
if BOT_AVAILABLE:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
else:
    bot = None

app = FastAPI(title="GarajHub Admin", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        print(f"Static files mounted from {static_dir}")
    else:
        print(f"Warning: Static folder not found at {static_dir}")
except Exception as e:
    print(f"Warning: Static files error: {e}")

_db_initialized = False

def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("GarajHub Web Server starting...")
    print(f"Port: {PORT}")
    print(f"Bot available: {BOT_AVAILABLE}")
    print(f"Database: {DB_PATH}")
    print("=" * 60)
    try:
        ensure_db()
        print("Database ready")
    except Exception as e:
        print(f"Database init warning: {e}")

@app.get("/")
async def root():
    return {
        "message": "GarajHub Bot API",
        "version": "2.0",
        "status": "running",
        "bot": "active" if BOT_AVAILABLE else "disabled",
        "endpoints": {
            "health": "/health",
            "admin": "/admin",
            "api_docs": "/docs",
            "statistics": "/api/statistics"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if os.path.exists(DB_PATH) else "missing",
        "bot": "available" if BOT_AVAILABLE else "unavailable",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/statistics")
async def get_statistics():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM startups')
        total_startups = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "active"')
        active_startups = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "pending"')
        pending_startups = cursor.fetchone()[0]
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) = ?', (today,))
        new_users_today = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM startups WHERE date(created_at) = ?', (today,))
        new_startups_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "total_users": total_users,
                "total_startups": total_startups,
                "active_startups": active_startups,
                "pending_startups": pending_startups,
                "new_users_today": new_users_today,
                "new_startups_today": new_startups_today,
                "uptime": get_uptime() # type: ignore
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# other endpoints copied from original server.py continue...

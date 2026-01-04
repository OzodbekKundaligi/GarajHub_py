# server.py
import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import jwt
import uvicorn
import asyncio
from pathlib import Path

# Telegram bot bilan integratsiya
import telebot
from telebot import types

# Konfiguratsiya
BOT_TOKEN = os.getenv('BOT_TOKEN', '8265294721:AAEWhiYC2zTYxPbFpYYFezZGNzKHUumoplE')
CHANNEL_USERNAME = '@GarajHub_uz'
ADMIN_ID = 7903688837
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI ilovasi
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server ishga tushganda
    print("🚀 Server ishga tushdi...")
    init_db()
    
    # Botni backgroundda ishga tushirish
    asyncio.create_task(run_bot())
    
    yield
    
    # Server to'xtaganda
    print("🛑 Server to'xtadi...")

app = FastAPI(title="GarajHub Admin API", version="1.0.0", lifespan=lifespan)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Productionda aniq domenlarni ko'rsating
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static fayllar
app.mount("/static", StaticFiles(directory="static"), name="static")

# Authentication
security = HTTPBearer()

# Database funksiyalari
def init_db():
    conn = sqlite3.connect('garajhub.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Adminlar jadvali
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
    
    # Foydalanuvchilar jadvali
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
    
    # Startuplar jadvali
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
            views INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users (user_id)
        )
    ''')
    
    # Startup a'zolari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS startup_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            startup_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (startup_id) REFERENCES startups (startup_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(startup_id, user_id)
        )
    ''')
    
    # Admin foydalanuvchi qo'shish (agar mavjud bo'lmasa)
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
    logging.info("Database initialized")

# Pydantic modellari
class LoginRequest(BaseModel):
    username: str
    password: str

class AdminCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    role: str = "admin"

class StartupCreate(BaseModel):
    name: str
    description: str
    group_link: str
    owner_id: int
    logo: Optional[str] = None

class StartupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    results: Optional[str] = None

class BroadcastMessage(BaseModel):
    message: str
    user_type: str = "all"  # all, active, inactive, startups, etc.

class StatisticsRequest(BaseModel):
    period: str = "week"  # day, week, month, year

# Authentication funksiyalari
def verify_password(plain_password, hashed_password):
    import hashlib
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def authenticate_admin(username: str, password: str):
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin and verify_password(password, admin[2]):
        return {
            "id": admin[0],
            "username": admin[1],
            "full_name": admin[3],
            "email": admin[4],
            "role": admin[5]
        }
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": admin[0],
        "username": admin[1],
        "full_name": admin[3],
        "email": admin[4],
        "role": admin[5]
    }

# Telegram bot funksiyalari (sizning botingizdan)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# WebSocket connections
connected_clients = []

# API endpointlari

# 1. Authentication
@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    admin = authenticate_admin(login_data.username, login_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Update last login
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (login_data.username,))
    conn.commit()
    conn.close()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": admin
    }

@app.get("/api/auth/me")
async def get_current_admin_info(admin: dict = Depends(get_current_admin)):
    return admin

# 2. Statistics
@app.get("/api/statistics")
async def get_statistics(admin: dict = Depends(get_current_admin)):
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    # Asosiy statistikalar
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups')
    total_startups = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "active"')
    active_startups = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "pending"')
    pending_startups = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "completed"')
    completed_startups = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE status = "rejected"')
    rejected_startups = cursor.fetchone()[0]
    
    # Bugungi statistika
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) = ?', (today,))
    new_users_today = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE date(created_at) = ?', (today,))
    new_startups_today = cursor.fetchone()[0]
    
    # Oylik o'sish
    last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) >= ?', (last_month,))
    users_last_month = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM startups WHERE date(created_at) >= ?', (last_month,))
    startups_last_month = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_users": total_users,
        "total_startups": total_startups,
        "active_startups": active_startups,
        "pending_startups": pending_startups,
        "completed_startups": completed_startups,
        "rejected_startups": rejected_startups,
        "new_users_today": new_users_today,
        "new_startups_today": new_startups_today,
        "users_last_month": users_last_month,
        "startups_last_month": startups_last_month,
        "user_growth_rate": round((users_last_month / total_users * 100), 2) if total_users > 0 else 0,
        "startup_growth_rate": round((startups_last_month / total_startups * 100), 2) if total_startups > 0 else 0
    }

@app.get("/api/statistics/chart/{chart_type}")
async def get_chart_data(chart_type: str, period: str = "week", admin: dict = Depends(get_current_admin)):
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    if chart_type == "user_growth":
        # Foydalanuvchi o'sishi
        if period == "week":
            days = 7
        elif period == "month":
            days = 30
        elif period == "quarter":
            days = 90
        else:  # year
            days = 365
        
        data = []
        labels = []
        
        for i in range(days, -1, -int(days/7)):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) <= ?', (date,))
            count = cursor.fetchone()[0]
            data.append(count)
            labels.append(date)
        
        conn.close()
        return {"labels": labels, "data": data}
    
    elif chart_type == "startup_distribution":
        # Startap taqsimoti
        cursor.execute('SELECT status, COUNT(*) FROM startups GROUP BY status')
        results = cursor.fetchall()
        
        labels = []
        data = []
        colors = []
        
        status_colors = {
            'active': '#4A6FA5',
            'pending': '#FF9F40',
            'completed': '#6DC5A3',
            'rejected': '#E74C3C'
        }
        
        for status, count in results:
            labels.append(status.capitalize())
            data.append(count)
            colors.append(status_colors.get(status, '#95A5A6'))
        
        conn.close()
        return {"labels": labels, "data": data, "colors": colors}
    
    elif chart_type == "activity":
        # Faollik grafigi
        if period == "week":
            days = 7
        else:
            days = 30
        
        labels = []
        startups_data = []
        users_data = []
        
        for i in range(days-1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM startups WHERE date(created_at) = ?', (date,))
            startups = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE date(joined_at) = ?', (date,))
            users = cursor.fetchone()[0]
            
            labels.append(date)
            startups_data.append(startups)
            users_data.append(users)
        
        conn.close()
        return {
            "labels": labels,
            "datasets": [
                {"label": "Startaplar", "data": startups_data, "borderColor": "#4A6FA5"},
                {"label": "Foydalanuvchilar", "data": users_data, "borderColor": "#6DC5A3"}
            ]
        }
    
    conn.close()
    raise HTTPException(status_code=404, detail="Chart not found")

# 3. Users management
@app.get("/api/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    conn = sqlite3.connect('garajhub.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    offset = (page - 1) * limit
    query = "SELECT * FROM users WHERE 1=1"
    params = []
    
    if search:
        query += " AND (first_name LIKE ? OR last_name LIKE ? OR username LIKE ? OR phone LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY joined_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    users = cursor.fetchall()
    
    # Total count
    count_query = "SELECT COUNT(*) FROM users WHERE 1=1"
    count_params = []
    
    if search:
        count_query += " AND (first_name LIKE ? OR last_name LIKE ? OR username LIKE ? OR phone LIKE ?)"
        count_params.extend([search_term, search_term, search_term, search_term])
    
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "users": [dict(user) for user in users],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@app.get("/api/users/{user_id}")
async def get_user(user_id: int, admin: dict = Depends(get_current_admin)):
    conn = sqlite3.connect('garajhub.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's startups
    cursor.execute('''
        SELECT s.* FROM startups s
        WHERE s.owner_id = ? OR s.startup_id IN (
            SELECT sm.startup_id FROM startup_members sm
            WHERE sm.user_id = ? AND sm.status = 'accepted'
        )
    ''', (user_id, user_id))
    user_startups = cursor.fetchall()
    
    # Get join requests
    cursor.execute('''
        SELECT sm.*, s.name as startup_name FROM startup_members sm
        JOIN startups s ON sm.startup_id = s.startup_id
        WHERE sm.user_id = ?
    ''', (user_id,))
    join_requests = cursor.fetchall()
    
    conn.close()
    
    return {
        "user": dict(user),
        "startups": [dict(s) for s in user_startups],
        "join_requests": [dict(r) for r in join_requests]
    }

@app.put("/api/users/{user_id}/status")
async def update_user_status(
    user_id: int, 
    status_data: dict, 
    admin: dict = Depends(get_current_admin)
):
    new_status = status_data.get("status")
    if new_status not in ["active", "inactive", "banned"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET status = ? WHERE user_id = ?', (new_status, user_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    conn.commit()
    conn.close()
    
    return {"message": f"User status updated to {new_status}"}

# 4. Startups management
@app.get("/api/startups")
async def get_startups(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    conn = sqlite3.connect('garajhub.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    offset = (page - 1) * limit
    query = '''
        SELECT s.*, u.first_name, u.last_name, u.username as owner_username,
               (SELECT COUNT(*) FROM startup_members sm WHERE sm.startup_id = s.startup_id AND sm.status = 'accepted') as member_count
        FROM startups s
        LEFT JOIN users u ON s.owner_id = u.user_id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += " AND (s.name LIKE ? OR s.description LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    if status:
        query += " AND s.status = ?"
        params.append(status)
    
    query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    startups = cursor.fetchall()
    
    # Total count
    count_query = "SELECT COUNT(*) FROM startups WHERE 1=1"
    count_params = []
    
    if search:
        count_query += " AND (name LIKE ? OR description LIKE ?)"
        count_params.extend([search_term, search_term])
    
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "startups": [dict(startup) for startup in startups],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@app.get("/api/startups/{startup_id}")
async def get_startup(startup_id: int, admin: dict = Depends(get_current_admin)):
    conn = sqlite3.connect('garajhub.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, u.first_name, u.last_name, u.username as owner_username,
               u.phone as owner_phone
        FROM startups s
        LEFT JOIN users u ON s.owner_id = u.user_id
        WHERE s.startup_id = ?
    ''', (startup_id,))
    startup = cursor.fetchone()
    
    if not startup:
        conn.close()
        raise HTTPException(status_code=404, detail="Startup not found")
    
    # Get members
    cursor.execute('''
        SELECT u.*, sm.joined_at, sm.status as member_status
        FROM startup_members sm
        JOIN users u ON sm.user_id = u.user_id
        WHERE sm.startup_id = ?
        ORDER BY sm.joined_at DESC
    ''', (startup_id,))
    members = cursor.fetchall()
    
    conn.close()
    
    return {
        "startup": dict(startup),
        "members": [dict(member) for member in members]
    }

@app.put("/api/startups/{startup_id}")
async def update_startup(
    startup_id: int, 
    startup_data: StartupUpdate, 
    admin: dict = Depends(get_current_admin)
):
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    # Get current startup
    cursor.execute('SELECT * FROM startups WHERE startup_id = ?', (startup_id,))
    startup = cursor.fetchone()
    
    if not startup:
        conn.close()
        raise HTTPException(status_code=404, detail="Startup not found")
    
    # Build update query
    update_fields = []
    params = []
    
    if startup_data.name is not None:
        update_fields.append("name = ?")
        params.append(startup_data.name)
    
    if startup_data.description is not None:
        update_fields.append("description = ?")
        params.append(startup_data.description)
    
    if startup_data.status is not None:
        update_fields.append("status = ?")
        params.append(startup_data.status)
        
        # Update timestamps based on status
        if startup_data.status == 'active' and startup[6] != 'active':
            update_fields.append("started_at = CURRENT_TIMESTAMP")
        elif startup_data.status == 'completed' and startup[6] != 'completed':
            update_fields.append("ended_at = CURRENT_TIMESTAMP")
    
    if startup_data.results is not None:
        update_fields.append("results = ?")
        params.append(startup_data.results)
    
    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(startup_id)
    
    update_query = f"UPDATE startups SET {', '.join(update_fields)} WHERE startup_id = ?"
    cursor.execute(update_query, params)
    
    conn.commit()
    conn.close()
    
    return {"message": "Startup updated successfully"}

@app.delete("/api/startups/{startup_id}")
async def delete_startup(startup_id: int, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can delete startups")
    
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM startup_members WHERE startup_id = ?', (startup_id,))
    cursor.execute('DELETE FROM startups WHERE startup_id = ?', (startup_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Startup not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Startup deleted successfully"}

# 5. Broadcast messages
@app.post("/api/broadcast")
async def broadcast_message(
    broadcast_data: BroadcastMessage, 
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin)
):
    background_tasks.add_task(send_broadcast_message, broadcast_data.message, broadcast_data.user_type)
    
    return {"message": "Broadcast started in background"}

async def send_broadcast_message(message_text: str, user_type: str):
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    # Get users based on type
    if user_type == "all":
        cursor.execute('SELECT user_id FROM users WHERE status = "active"')
    elif user_type == "startup_owners":
        cursor.execute('SELECT DISTINCT owner_id FROM startups WHERE status = "active"')
    elif user_type == "startup_members":
        cursor.execute('''
            SELECT DISTINCT sm.user_id FROM startup_members sm
            WHERE sm.status = "accepted"
        ''')
    else:
        conn.close()
        return
    
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user_id_tuple in users:
        user_id = user_id_tuple[0]
        try:
            bot.send_message(
                user_id,
                f"📢 <b>Admin xabari:</b>\n\n{message_text}\n\n"
                f"<i>— GarajHub jamoasi</i>"
            )
            success += 1
        except Exception as e:
            failed += 1
        
        # Har 10 ta xabardan keyin 1 sekund pauza
        if (success + failed) % 10 == 0:
            await asyncio.sleep(1)
    
    # Send report to admin
    try:
        bot.send_message(
            ADMIN_ID,
            f"📊 <b>Xabar yuborish hisoboti</b>\n\n"
            f"✅ Yuborildi: {success}\n"
            f"❌ Yuborilmadi: {failed}\n"
            f"📝 Xabar: {message_text[:100]}..."
        )
    except:
        pass

# 6. Admin management
@app.get("/api/admins")
async def get_admins(admin: dict = Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can view admins")
    
    conn = sqlite3.connect('garajhub.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, full_name, email, role, created_at, last_login FROM admins')
    admins = cursor.fetchall()
    
    conn.close()
    
    return {"admins": [dict(a) for a in admins]}

@app.post("/api/admins")
async def create_admin(new_admin: AdminCreate, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can create admins")
    
    import hashlib
    hashed_password = hashlib.sha256(new_admin.password.encode()).hexdigest()
    
    conn = sqlite3.connect('garajhub.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO admins (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (new_admin.username, hashed_password, new_admin.full_name, new_admin.email, new_admin.role))
        
        conn.commit()
        admin_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    conn.close()
    
    return {"message": "Admin created successfully", "admin_id": admin_id}

# 7. WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back (you can add more logic here)
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

async def send_websocket_update(event_type: str, data: dict):
    """Send update to all connected WebSocket clients"""
    message = {"event": event_type, "data": data, "timestamp": datetime.now().isoformat()}
    
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass

# 8. Bot integration functions
async def run_bot():
    """Run Telegram bot in background"""
    print("🤖 Bot ishga tushmoqda...")
    
    # Import bot handlers from main.py
    from main import bot as telegram_bot
    
    # Start polling
    telegram_bot.infinity_polling(timeout=60, long_polling_timeout=60)

# 9. Serve admin panel
@app.get("/")
async def serve_admin_panel():
    return FileResponse("templates/index.html")

@app.get("/admin/{path:path}")
async def serve_admin_static(path: str):
    try:
        return FileResponse(f"templates/{path}")
    except:
        raise HTTPException(status_code=404)

# 10. Backup database
@app.get("/api/backup")
async def backup_database(admin: dict = Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can backup database")
    
    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    import shutil
    shutil.copy2('garajhub.db', backup_file)
    
    return {
        "message": "Backup created successfully",
        "filename": backup_file,
        "download_url": f"/api/backup/{backup_file}"
    }

@app.get("/api/backup/{filename}")
async def download_backup(filename: str, admin: dict = Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can download backups")
    
    if not filename.startswith("backup_") or not filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid backup file")
    
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    return FileResponse(filename, filename=filename)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
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
    print("⚠️ pyTelegramBotAPI not installed, bot will not work")

# ===== KONFIGURATSIYA =====
BOT_TOKEN = os.getenv('BOT_TOKEN', '8265294721:AAEWhiYC2zTYxPbFpYYFezZGNzKHUumoplE')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@GarajHub_uz')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7903688837'))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
PORT = int(os.getenv('PORT', '8000'))

# ===== DATABASE =====
def get_db_path():
    """Railway uchun database fayl joyini aniqlash"""
    if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
        return os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'garajhub.db')
    elif 'RAILWAY_STORAGE_DIR' in os.environ:
        return os.path.join(os.environ['RAILWAY_STORAGE_DIR'], 'garajhub.db')
    else:
        return 'garajhub.db'

DB_PATH = get_db_path()

def init_db():
    """Database yaratish"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
            views INTEGER DEFAULT 0
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
            UNIQUE(startup_id, user_id)
        )
    ''')
    
    # Dastlabki admin qo'shish
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
    print(f"✅ Database initialized at: {DB_PATH}")

# ===== TELEGRAM BOT =====
if BOT_AVAILABLE:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
else:
    bot = None

# ===== FASTAPI APP =====
app = FastAPI(title="GarajHub Admin", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://garajhub.vercel.app",  # Vercel frontend URL
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    print("⚠️ Static folder not found")

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    """Server ishga tushganda"""
    print("=" * 60)
    print("🚀 GarajHub Bot Server ishga tushdi...")
    print(f"🔧 Port: {PORT}")
    print(f"🤖 Bot available: {BOT_AVAILABLE}")
    print(f"💾 Database: {DB_PATH}")
    print("=" * 60)
    
    init_db()
    
    # Bot polling disabled in FastAPI mode - run main.py separately for bot
    if BOT_AVAILABLE:
        print("⚠️ Telegram Bot API integration active, but polling disabled")
        print("💡 Run 'python main.py' separately for bot polling functionality")

# ===== BOT FUNCTIONS =====
async def run_bot_async():
    """Botni backgroundda ishga tushirish - NOT USED"""
    if not BOT_AVAILABLE or not bot:
        print("❌ Bot is not available")
        return
    print("⚠️ Bot polling should be run from main.py, not here")

# ===== API ENDPOINTS =====

# 1. Asosiy endpointlar
@app.get("/")
async def root():
    """Asosiy sahifa"""
    return {
        "message": "GarajHub Bot API",
        "version": "2.0",
        "status": "running",
        "bot": "active" if BOT_AVAILABLE else "disabled",
        "endpoints": {
            "health": "/health",
            "admin": "http://localhost:8000/admin",
            "api_docs": "/docs",
            "statistics": "/api/statistics"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected" if os.path.exists(DB_PATH) else "missing",
        "bot": "available" if BOT_AVAILABLE else "unavailable",
        "timestamp": datetime.now().isoformat()
    }

# 2. Statistika API
@app.get("/api/statistics")
async def get_statistics():
    """Umumiy statistikalar"""
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
        
        # Bugungi statistikalar
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
                "uptime": get_uptime()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 3. Foydalanuvchilar API
@app.get("/api/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None
):
    """Foydalanuvchilarni olish"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        if search:
            query = '''
                SELECT * FROM users 
                WHERE first_name LIKE ? OR last_name LIKE ? OR username LIKE ?
                ORDER BY joined_at DESC 
                LIMIT ? OFFSET ?
            '''
            search_term = f"%{search}%"
            cursor.execute(query, (search_term, search_term, search_term, limit, offset))
        else:
            cursor.execute('SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?', (limit, offset))
        
        users = cursor.fetchall()
        
        # Jami soni
        if search:
            cursor.execute('SELECT COUNT(*) FROM users WHERE first_name LIKE ? OR last_name LIKE ? OR username LIKE ?', 
                          (search_term, search_term, search_term))
        else:
            cursor.execute('SELECT COUNT(*) FROM users')
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return {
            "success": True,
            "users": [dict(user) for user in users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 4. Startaplar API
@app.get("/api/startups")
async def get_startups(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None
):
    """Startaplarni olish"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        if status:
            query = '''
                SELECT s.*, u.first_name, u.last_name 
                FROM startups s
                LEFT JOIN users u ON s.owner_id = u.user_id
                WHERE s.status = ?
                ORDER BY s.created_at DESC 
                LIMIT ? OFFSET ?
            '''
            cursor.execute(query, (status, limit, offset))
        else:
            query = '''
                SELECT s.*, u.first_name, u.last_name 
                FROM startups s
                LEFT JOIN users u ON s.owner_id = u.user_id
                ORDER BY s.created_at DESC 
                LIMIT ? OFFSET ?
            '''
            cursor.execute(query, (limit, offset))
        
        startups = cursor.fetchall()
        
        # Jami soni
        if status:
            cursor.execute('SELECT COUNT(*) FROM startups WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT COUNT(*) FROM startups')
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return {
            "success": True,
            "startups": [dict(startup) for startup in startups],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 5. Xabar yuborish API
@app.post("/api/broadcast")
async def broadcast_message(request: Request, background_tasks: BackgroundTasks):
    """Xabar yuborish"""
    try:
        data = await request.json()
        message = data.get('message', '')
        user_type = data.get('user_type', 'all')
        
        if not message:
            return {"success": False, "error": "Message is required"}
        
        if BOT_AVAILABLE:
            # Background task sifatida xabar yuborish
            background_tasks.add_task(send_broadcast_task, message, user_type)
            
            return {
                "success": True,
                "message": "Xabar yuborish boshlandi",
                "user_type": user_type
            }
        else:
            return {
                "success": False,
                "error": "Bot is not available"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def send_broadcast_task(message: str, user_type: str):
    """Background task: xabar yuborish"""
    if not BOT_AVAILABLE or not bot:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Foydalanuvchilarni tanlash
        if user_type == "all":
            cursor.execute('SELECT user_id FROM users WHERE status = "active"')
        elif user_type == "startup_owners":
            cursor.execute('SELECT DISTINCT owner_id FROM startups WHERE status = "active"')
        else:
            conn.close()
            return
        
        users = cursor.fetchall()
        conn.close()
        
        sent = 0
        failed = 0
        
        for user_id_tuple in users:
            user_id = user_id_tuple[0]
            try:
                bot.send_message(
                    user_id,
                    f"📢 <b>GarajHub yangiligi:</b>\n\n{message}\n\n"
                    f"<i>— GarajHub jamoasi</i>"
                )
                sent += 1
            except:
                failed += 1
            
            # 0.1 sekund pauza
            await asyncio.sleep(0.1)
        
        print(f"✅ Xabar yuborildi: {sent} ta, Yuborilmadi: {failed} ta")
        
    except Exception as e:
        print(f"❌ Xabar yuborishda xatolik: {e}")

# 6. Admin authentication
@app.post("/api/auth/login")
async def admin_login(request: Request):
    """Admin login"""
    try:
        data = await request.json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        if not username or not password:
            return {"success": False, "error": "Username va password kerak"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            import hashlib
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            if hashed_password == admin[2]:  # admin[2] = password
                # Update last login
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (username,))
                conn.commit()
                conn.close()
                
                return {
                    "success": True,
                    "admin": {
                        "id": admin[0],
                        "username": admin[1],
                        "full_name": admin[3],
                        "email": admin[4],
                        "role": admin[5]
                    },
                    "message": "Muvaffaqiyatli kirildi"
                }
        
        return {"success": False, "error": "Noto'g'ri login yoki parol"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 7. Admin panel sahifasi
@app.get("/admin")
async def admin_panel():
    """Admin panel HTML sahifasi"""
    try:
        return FileResponse("templates/index.html")
    except:
        # Agar template topilmasa, oddiy HTML qaytarish
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GarajHub Admin Panel</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }
                .btn { background: #4A6FA5; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 GarajHub Admin Panel</h1>
                <p>Server ishlayapti. Admin panel to'liq versiyasi tez orada qo'shiladi.</p>
                
                <div class="card">
                    <h2>🔧 Server ma'lumotlari</h2>
                    <p><strong>Status:</strong> ✅ Ishlamoqda</p>
                    <p><strong>Port:</strong> """ + str(PORT) + """</p>
                    <p><strong>Bot:</strong> """ + ("✅ Faol" if BOT_AVAILABLE else "❌ O'chirilgan") + """</p>
                    <p><strong>Database:</strong> """ + ("✅ Mavjud" if os.path.exists(DB_PATH) else "❌ Topilmadi") + """</p>
                </div>
                
                <div class="card">
                    <h2>📊 Tezkor harakatlar</h2>
                    <button class="btn" onclick="window.location.href='/health'">Server holati</button>
                    <button class="btn" onclick="window.location.href='/api/statistics'">Statistika</button>
                    <button class="btn" onclick="window.location.href='/docs'">API Docs</button>
                </div>
                
                <div class="card">
                    <h2>🔗 Foydali havolalar</h2>
                    <p>• <a href="/api/statistics">Statistika API</a></p>
                    <p>• <a href="/api/users">Foydalanuvchilar</a></p>
                    <p>• <a href="/api/startups">Startaplar</a></p>
                    <p>• <a href="/health">Server holati</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

# 8. Utility functions
def get_uptime():
    """Server uptime"""
    if hasattr(app, 'startup_time'):
        uptime = datetime.now() - app.startup_time
        return str(uptime).split('.')[0]
    return "0:00:00"

# ===== RAILWAY SPECIFIC =====
# Railway uchun maxsus sozlamalar
if __name__ == "__main__":
    # Server vaqti
    app.startup_time = datetime.now()
    
    # Railway portini olish
    port = int(os.environ.get("PORT", PORT))
    
    print(f"🌐 Server {port} portida ishga tushmoqda...")
    print(f"📡 URL: http://0.0.0.0:{port}")
    print(f"🔗 Admin panel: http://0.0.0.0:{port}/admin")
    print(f"📊 API: http://0.0.0.0:{port}/api/statistics")
    
    # Uvicorn serverini ishga tushirish
    uvicorn.run(
        app,
        host="0.0.0.0",  # Railway uchun
        port=port,
        log_level="info",
        access_log=True
    )
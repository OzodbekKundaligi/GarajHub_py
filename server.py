import os
import sqlite3
from fastapi import FastAPI
import uvicorn

# ===== KONFIGURATSIYA =====
PORT = int(os.environ.get("PORT", 8000))
DB_PATH = "garajhub.db"

# ===== FASTAPI APP =====
app = FastAPI(title="GarajHub Bot", version="1.0")

# ===== DATABASE =====
def init_db():
    """Oddiy database yaratish"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS startups (
            startup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database yaratildi: {DB_PATH}")

# ===== API ENDPOINTS =====

@app.get("/")
async def root():
    return {
        "message": "🚀 GarajHub Bot API",
        "status": "running",
        "version": "1.0",
        "endpoints": {
            "health": "/health",
            "stats": "/api/stats",
            "users": "/api/users"
        }
    }

@app.get("/health")
async def health_check():
    """Health check - MUHIM! Railway shu endpointni tekshiradi"""
    try:
        # Database connectionni tekshirish
        conn = sqlite3.connect(DB_PATH)
        conn.close()
        db_status = "connected"
    except:
        db_status = "error"
    
    return {
        "status": "healthy",
        "timestamp": "2024",
        "database": db_status,
        "service": "GarajHub Bot"
    }

@app.get("/api/stats")
async def get_stats():
    """Statistika"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM startups")
    startups = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "users": users,
        "startups": startups,
        "active": True
    }

@app.get("/api/users")
async def get_users():
    """Foydalanuvchilar"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT 20")
    users = cursor.fetchall()
    
    conn.close()
    
    return {
        "users": [dict(user) for user in users],
        "count": len(users)
    }

# ===== STARTUP =====
@app.on_event("startup")
async def startup():
    """Server ishga tushganda"""
    print("=" * 50)
    print("🚀 GarajHub Bot Server ishga tushdi")
    print(f"🌐 Port: {PORT}")
    print(f"📁 Database: {DB_PATH}")
    print("=" * 50)
    
    init_db()

# ===== MAIN =====
if __name__ == "__main__":
    print(f"✅ Server {PORT} portida ishga tushmoqda...")
    print(f"🔗 Health check: http://0.0.0.0:{PORT}/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
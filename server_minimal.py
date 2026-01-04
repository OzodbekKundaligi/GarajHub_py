"""
GarajHub - Railway Deployment Version
Minimized for fast startup
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# FastAPI imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

print("✅ Starting GarajHub server...", file=sys.stderr, flush=True)

# Configuration
PORT = int(os.getenv("PORT", "8000"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "0")

print(f"🔧 Port: {PORT}", file=sys.stderr, flush=True)
print(f"🤖 Bot Token: {'✅ Set' if BOT_TOKEN else '⚠️ Not set'}", file=sys.stderr, flush=True)

# Create FastAPI app
app = FastAPI(title="GarajHub", version="2.0")
print("✅ FastAPI app created", file=sys.stderr, flush=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("✅ CORS configured", file=sys.stderr, flush=True)

# Mount static files if they exist
try:
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        print(f"✅ Static files mounted", file=sys.stderr, flush=True)
except Exception as e:
    print(f"⚠️ Static files: {e}", file=sys.stderr, flush=True)

# ===== ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GarajHub API",
        "version": "2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/admin")
async def admin_panel():
    """Admin panel"""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    
    # Fallback HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GarajHub Admin</title>
        <style>
            body { font-family: Arial; margin: 40px; background: #f9f9f9; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 GarajHub Admin Panel</h1>
            <p>✅ Server is running!</p>
            <a href="/docs">📖 API Documentation</a>
            <a href="/health">🏥 Health Check</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/statistics")
async def statistics():
    """Statistics endpoint"""
    return {
        "total_users": 0,
        "total_startups": 0,
        "timestamp": datetime.now().isoformat()
    }

# ===== STARTUP AND RUN =====

if __name__ == "__main__":
    print("=" * 60, file=sys.stderr, flush=True)
    print("🚀 GarajHub Server Starting", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)
    
    try:
        print(f"📡 Starting on 0.0.0.0:{PORT}", file=sys.stderr, flush=True)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional
import hashlib
import sqlite3

# =========================
# Basic App
# =========================
app = FastAPI(title="MCP Directory Analyzer Server")

BASE_DIR = Path(__file__).parent
BOOK_DIR = BASE_DIR / "data" / "books"
DB_PATH = BASE_DIR / "summaries.db"

BOOK_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Health Check
# =========================
@app.get("/health")
def health_check():
    health_status = {
        "status": "healthy",
        "service": "MCP Directory Analyzer Server",
        "database": "unknown"
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

# =========================
# DB Init
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        document_id TEXT PRIMARY KEY,
        filename TEXT,
        summary TEXT,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# Utilities
# =========================
def file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

# =========================
# Request Models (Body-only)
# =========================
class ListDirectoryRequest(BaseModel):
    path: str

class ReadDocumentChunkRequest(BaseModel):
    path: str
    offset: int = 0
    chunk_size: int = 2000

class SaveSummaryRequest(BaseModel):
    document_id: str
    filename: str
    summary: str
    status: str  # completed | failed

# =========================
# MCP Tool Schemas
# =========================
@app.get("/mcp/tools")
def mcp_tools():
    return {
        "tools": [
            {
                "name": "list_directory",
                "description": "List documents in a directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "read_document_chunk",
                "description": "Read a document in chunks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "offset": {"type": "integer", "default": 0},
                        "chunk_size": {"type": "integer", "default": 2000}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "save_summary_to_db",
                "description": "Save document summary to database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "filename": {"type": "string"},
                        "summary": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["completed", "failed"]
                        }
                    },
                    "required": ["document_id", "filename", "summary", "status"]
                }
            }
        ]
    }

# =========================
# Tool: list_directory (Body-only)
# =========================
@app.post("/list_directory")
def list_directory(req: ListDirectoryRequest):
    directory = Path(req.path)
    if not directory.exists():
        raise HTTPException(404, "Directory not found")

    files = [
        {
            "name": f.name,
            "path": str(f),
            "is_dir": f.is_dir()
        }
        for f in directory.iterdir()
        if f.suffix.lower() in [".txt", ".md", ".pdf"]
    ]

    return {
        "path": str(directory),
        "files": files
    }

# =========================
# Tool: read_document_chunk (Body-only)
# =========================
@app.post("/read_document_chunk")
def read_document_chunk(req: ReadDocumentChunkRequest):
    path = Path(req.path)
    
    # 1. 基础检查
    if not path.exists():
        raise HTTPException(404, f"File not found: {path}")
    
    # 2. 读取全文 (针对文本格式如 .md, .txt)
    try:
        # 使用 utf-8 编码读取，ignore 忽略非法字符防止崩溃
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(500, f"Error reading file: {str(e)}")

    # 3. 计算分块位置
    total_len = len(text)
    start = max(0, req.offset)
    end = min(total_len, start + req.chunk_size)

    # 4. 截取内容
    chunk = text[start:end]
    eof = end >= total_len # 是否已到达文件末尾

    # 5. 返回丰富元数据，帮助 LLM 判断进度
    return {
        "path": str(path),
        "filename": path.name,
        "offset": start,
        "next_offset": end if not eof else None,
        "chunk_size": len(chunk),
        "total_length": total_len,
        "progress": f"{round((end/total_len)*100, 1)}%" if total_len > 0 else "0%",
        "eof": eof,
        "content": chunk
    }

# =========================
# Tool: save_summary_to_db (Body-only)
# =========================
@app.post("/save_summary_to_db")
def save_summary_to_db(req: SaveSummaryRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO summaries
    (document_id, filename, summary, status)
    VALUES (?, ?, ?, ?)
    """, (req.document_id, req.filename, req.summary, req.status))

    conn.commit()
    conn.close()

    return {
        "document_id": req.document_id,
        "filename": req.filename,
        "status": req.status,
        "saved": True
    }

# =========================
# Entrypoint
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3333)

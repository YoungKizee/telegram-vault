import os
import uvicorn
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx

# Configurations
BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID") 
KVDB_BUCKET = os.getenv("KVDB_BUCKET") # Your new permanent cloud database

vault_db = {} 

# --- DATABASE SYNC LOGIC ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Fetches your saved folders and files when the server wakes up"""
    global vault_db
    if KVDB_BUCKET:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"https://kvdb.io/{KVDB_BUCKET}/vault")
                if res.status_code == 200 and res.text:
                    vault_db = res.json()
            except Exception:
                pass
    yield

async def save_db():
    """Saves data instantly to the cloud every time you upload or create a folder"""
    if KVDB_BUCKET:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"https://kvdb.io/{KVDB_BUCKET}/vault", json=vault_db)
            except Exception:
                pass

app = FastAPI(lifespan=lifespan)

# --- AESTHETIC CINEMATIC FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VaultOS Cinematic</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
            body { 
                background-color: #030305; 
                background-image: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #030305 60%);
                color: #e5e5e5; 
                font-family: 'Inter', sans-serif; 
                min-height: 100vh;
            }
            .glass-panel { 
                background: rgba(255, 255, 255, 0.02); 
                backdrop-filter: blur(16px); 
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.05); 
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
            }
            .cinematic-glow { text-shadow: 0 0 20px rgba(167, 139, 250, 0.4); }
            .item-hover:hover { background: rgba(255, 255, 255, 0.05); border-color: rgba(167, 139, 250, 0.3); }
        </style>
    </head>
    <body class="p-6 max-w-2xl mx-auto">
        
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-3xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-indigo-500 cinematic-glow">VaultOS</h1>
                <p class="text-xs text-indigo-300/50 tracking-widest uppercase mt-1">Cinematic Cloud Engine</p>
            </div>
            <div class="text-xs px-3 py-1 rounded-full border border-indigo-500/30 text-indigo-400 glass-panel">LIVE</div>
        </div>

        <div class="flex gap-3 mb-6">
            <button onclick="createFolder()" class="glass-panel flex-1 py-3 rounded-xl flex items-center justify-center gap-2 text-sm font-medium hover:bg-white/5 transition">
                <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path></svg>
                New Folder
            </button>
            <div class="glass-panel flex-1 relative rounded-xl hover:bg-white/5 transition flex items-center justify-center">
                <input type="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onchange="uploadFile()" />
                <div class="flex items-center justify-center gap-2 text-sm font-medium">
                    <svg class="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    Upload File
                </div>
            </div>
        </div>

        <div class="flex items-center gap-2 mb-4 text-sm text-gray-400" id="breadcrumbs">
            <button onclick="navigateTo('root')" class="hover:text-violet-400 transition">My Drive</button>
        </div>

        <div id="driveGrid" class="grid grid-cols-2 gap-4">
            </div>

        <script>
            let currentFolder = 'root';
            let folderHistory = [{id: 'root', name: 'My Drive'}];

            async function loadItems() {
                const res = await fetch(`/api/items?parent_id=${currentFolder}`);
                const items = await res.json();
                const grid = document.getElementById('driveGrid');
                grid.innerHTML = '';
                
                if (Object.keys(items).length === 0) {
                    grid.innerHTML = `<div class="col-span-2 text-center py-12 text-gray-600 text-sm">This folder is empty.</div>`;
                    return;
                }

                // Render Folders First, then Files
                for (const [id, item] of Object.entries(items)) {
                    if (item.type === 'folder') {
                        grid.innerHTML += `
                            <div onclick="navigateTo('${id}', '${item.name}')" class="glass-panel p-4 rounded-2xl item-hover cursor-pointer transition flex flex-col items-center justify-center text-center h-32 gap-3 group">
                                <svg class="w-10 h-10 text-indigo-400/70 group-hover:text-indigo-400 transition" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                <span class="text-sm font-medium text-gray-300 truncate w-full px-2">${item.name}</span>
                            </div>`;
                    } else {
                        grid.innerHTML += `
                            <div class="glass-panel p-4 rounded-2xl item-hover transition flex flex-col items-center justify-center text-center h-32 gap-3 group relative">
                                <svg class="w-9 h-9 text-gray-500 group-hover:text-violet-400 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                                <span class="text-xs font-medium text-gray-400 truncate w-full px-2">${item.name}</span>
                                <a href="/api/download/${id}" target="_blank" class="absolute inset-0 z-10"></a>
                            </div>`;
                    }
                }
            }

            function navigateTo(folderId, folderName) {
                if (folderId === 'root') {
                    folderHistory = [{id: 'root', name: 'My Drive'}];
                } else {
                    folderHistory.push({id: folderId, name: folderName});
                }
                currentFolder = folderId;
                updateBreadcrumbs();
                loadItems();
            }

            function updateBreadcrumbs() {
                const bc = document.getElementById('breadcrumbs');
                bc.innerHTML = folderHistory.map((f, index) => {
                    const isLast = index === folderHistory.length - 1;
                    return `<span class="cursor-pointer ${isLast ? 'text-violet-400 font-medium' : 'hover:text-violet-400 transition'}" 
                                  onclick="navigateTo('${f.id}')">${f.name}</span>`;
                }).join(' <span class="text-gray-600">/</span> ');
            }

            async function createFolder() {
                const folderName = prompt("Enter folder name:");
                if (!folderName) return;
                
                await fetch('/api/folders', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name: folderName, parent_id: currentFolder })
                });
                loadItems();
            }

            async function uploadFile() {
                const input = document.getElementById('fileInput');
                if(input.files.length === 0) return;
                
                const formData = new FormData();
                formData.append('file', input.files[0]);
                formData.append('parent_id', currentFolder);
                
                input.value = ''; 
                
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                if(res.ok) loadItems();
                else alert("Upload failed.");
            }

            loadItems();
        </script>
    </body>
    </html>
    """

# --- BACKEND API ROUTES ---

class FolderRequest(BaseModel):
    name: str
    parent_id: str

@app.post("/api/folders")
async def create_new_folder(req: FolderRequest):
    folder_id = "fld_" + str(uuid.uuid4())[:8]
    vault_db[folder_id] = {
        "type": "folder",
        "name": req.name,
        "parent_id": req.parent_id,
        "tg_id": None
    }
    await save_db()  # <-- Triggers permanent save
    return {"success": True, "id": folder_id}

@app.post("/api/upload")
async def upload_file(parent_id: str = Form(...), file: UploadFile = File(...)):
    if not BOT_TOKEN or not STORAGE_CHANNEL_ID:
        raise HTTPException(status_code=500, detail="Server config missing.")
        
    file_bytes = await file.read()
    
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            telegram_url,
            data={"chat_id": STORAGE_CHANNEL_ID},
            files={"document": (file.filename, file_bytes)}
        )
        res_data = response.json()
        
    if not res_data.get("ok"):
        raise HTTPException(status_code=500, detail="Telegram cloud transfer failed.")

    tg_file_id = res_data["result"]["document"]["file_id"]
    db_id = "doc_" + str(uuid.uuid4())[:8]
    
    vault_db[db_id] = {
        "type": "file",
        "name": file.filename, 
        "parent_id": parent_id,
        "tg_id": tg_file_id
    }
    await save_db()  # <-- Triggers permanent save
    return {"success": True}

@app.get("/api/items")
async def get_items(parent_id: str = "root"):
    return {k: v for k, v in vault_db.items() if v.get("parent_id") == parent_id}

@app.get("/api/download/{item_id}")
async def download_file(item_id: str):
    if item_id not in vault_db or vault_db[item_id]["type"] == "folder":
        raise HTTPException(status_code=404, detail="File missing.")
    
    tg_id = vault_db[item_id]["tg_id"]
    async with httpx.AsyncClient() as client:
        info = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={tg_id}")
        file_path = info.json()["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        return HTMLResponse(f"<script>window.location.href='{download_url}';</script>")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
    

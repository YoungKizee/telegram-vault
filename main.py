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
KVDB_BUCKET = os.getenv("KVDB_BUCKET") 

vault_db = {} 

# --- DATABASE SYNC LOGIC ---
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    if KVDB_BUCKET:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"https://kvdb.io/{KVDB_BUCKET}/vault", json=vault_db)
            except Exception:
                pass

app = FastAPI(lifespan=lifespan)

# --- ADVANCED CINEMATIC FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SENZ1 Storage Engine</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
            body { 
                background-color: #020204; 
                background-image: radial-gradient(circle at 50% 0%, #1e1145 0%, #020204 70%);
                color: #e2e8f0; 
                font-family: 'Inter', sans-serif; 
                min-height: 100vh;
            }
            .glass { 
                background: rgba(255, 255, 255, 0.02); 
                backdrop-filter: blur(20px); 
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.04); 
            }
            .glow-text { text-shadow: 0 0 25px rgba(139, 92, 246, 0.5); }
            .glow-border:focus { border-color: rgba(139, 92, 246, 0.5); box-shadow: 0 0 15px rgba(139, 92, 246, 0.15); }
        </style>
    </head>
    <body class="p-4 max-w-3xl mx-auto pb-24">
        
        <div class="flex justify-between items-center mb-6">
            <div>
                <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 tracking-tight glow-text">SENZ1</h1>
            </div>
            <div class="text-xs px-3 py-1 rounded-full border border-emerald-500/30 text-emerald-400 font-mono bg-emerald-500/5">CLOUD SECURE</div>
        </div>

        <div id="progressContainer" class="hidden mb-6">
            <div class="flex justify-between text-xs text-violet-400 font-mono mb-1">
                <span id="progressText">Uploading...</span>
                <span id="progressPercent">0%</span>
            </div>
            <div class="w-full bg-gray-900 rounded-full h-1.5 border border-white/5 overflow-hidden">
                <div id="progressBar" class="bg-gradient-to-r from-violet-500 to-fuchsia-500 h-1.5 rounded-full" style="width: 0%; transition: width 0.2s;"></div>
            </div>
        </div>

        <div class="relative mb-4">
            <input type="text" id="searchBar" oninput="loadItems()" placeholder="Search drive files, packages, folders..." class="w-full glass rounded-xl py-3 pl-10 pr-4 text-sm outline-none transition glow-border text-gray-200 placeholder-gray-600" />
            <svg class="w-4 h-4 absolute left-3.5 top-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </div>

        <div class="flex gap-2.5 mb-6">
            <button onclick="createFolder()" class="glass flex-1 py-3.5 rounded-xl flex items-center justify-center gap-2 text-xs font-semibold hover:bg-white/5 transition border border-white/5">
                <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path></svg>
                New Folder
            </button>
            <div class="glass flex-1 relative rounded-xl hover:bg-white/5 transition border border-white/5 flex items-center justify-center">
                <input type="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onchange="uploadFile()" />
                <div class="flex items-center justify-center gap-2 text-xs font-semibold">
                    <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    Upload File
                </div>
            </div>
        </div>

        <div class="flex gap-2 overflow-x-auto pb-3 mb-4 text-xs scrollbar-none" id="typeFilters">
            <button onclick="filterByType('all')" id="filter-all" class="px-4 py-2 rounded-lg font-medium bg-violet-600 text-white transition shrink-0">All Items</button>
            <button onclick="filterByType('image')" id="filter-image" class="glass px-4 py-2 rounded-lg font-medium text-gray-400 hover:text-white transition shrink-0">Images</button>
            <button onclick="filterByType('video')" id="filter-video" class="glass px-4 py-2 rounded-lg font-medium text-gray-400 hover:text-white transition shrink-0">Videos</button>
            <button onclick="filterByType('audio')" id="filter-audio" class="glass px-4 py-2 rounded-lg font-medium text-gray-400 hover:text-white transition shrink-0">Audio</button>
            <button onclick="filterByType('document')" id="filter-document" class="glass px-4 py-2 rounded-lg font-medium text-gray-400 hover:text-white transition shrink-0">Documents</button>
        </div>

        <div class="flex items-center gap-2 mb-4 text-xs font-medium px-2 bg-white/5 py-2 rounded-lg border border-white/5">
            <div class="flex gap-1 border-r border-white/10 pr-2 mr-1">
                <button onclick="navBack()" class="p-1.5 rounded bg-black/20 text-gray-400 hover:text-white hover:bg-white/10 transition" title="Back">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7"></path></svg>
                </button>
                <button onclick="navForward()" class="p-1.5 rounded bg-black/20 text-gray-400 hover:text-white hover:bg-white/10 transition" title="Forward">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"></path></svg>
                </button>
            </div>
            <div class="flex items-center gap-1.5 flex-wrap" id="breadcrumbs">
                <button onclick="jumpToRoot()" class="hover:text-violet-400 transition">My Drive</button>
            </div>
        </div>

        <div id="driveGrid" class="grid grid-cols-2 gap-3">
            </div>

        <script>
            let currentFolder = 'root';
            // Navigation stack variables
            let navStack = [{id: 'root', name: 'My Drive'}];
            let navIndex = 0; 

            let activeTypeFilter = 'all';

            function getFileBadge(filename) {
                const ext = filename.split('.').pop().toLowerCase();
                let color = "bg-gray-500/10 text-gray-400 border-gray-500/20";
                
                if (['jpg','jpeg','png','gif','webp','svg'].includes(ext)) color = "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
                else if (['mp4','mkv','avi','mov'].includes(ext)) color = "bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20";
                else if (['mp3','wav','flac','ogg'].includes(ext)) color = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                else if (['pdf','doc','docx','txt','zip','rar','exe','msi'].includes(ext)) color = "bg-amber-500/10 text-amber-400 border-amber-500/20";
                
                return `<span class="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${color} font-mono relative z-20 shadow-lg shadow-black/50 bg-black/50 backdrop-blur-md">${ext}</span>`;
            }

            async function loadItems() {
                const res = await fetch(`/api/items?parent_id=${currentFolder}`);
                let items = await res.json();
                
                const searchQuery = document.getElementById('searchBar').value.toLowerCase();
                const grid = document.getElementById('driveGrid');
                grid.innerHTML = '';
                
                let itemList = Object.entries(items).map(([id, data]) => ({id, ...data}));
                
                if(searchQuery) {
                    itemList = itemList.filter(i => i.name.toLowerCase().includes(searchQuery));
                }

                if(activeTypeFilter !== 'all') {
                    itemList = itemList.filter(item => {
                        if (item.type === 'folder') return false;
                        const ext = item.name.split('.').pop().toLowerCase();
                        if (activeTypeFilter === 'image') return ['jpg','jpeg','png','gif','webp'].includes(ext);
                        if (activeTypeFilter === 'video') return ['mp4','mkv','avi','mov'].includes(ext);
                        if (activeTypeFilter === 'audio') return ['mp3','wav','flac','ogg'].includes(ext);
                        if (activeTypeFilter === 'document') return ['pdf','doc','docx','txt','zip','rar'].includes(ext);
                        return true;
                    });
                }

                // SORTING ENGINE: Always push folders to the top, then sort alphabetically A-Z
                itemList.sort((a, b) => {
                    if (a.type === 'folder' && b.type !== 'folder') return -1;
                    if (a.type !== 'folder' && b.type === 'folder') return 1;
                    return a.name.localeCompare(b.name);
                });

                if (itemList.length === 0) {
                    grid.innerHTML = `<div class="col-span-full text-center py-16 text-gray-600 text-xs tracking-wider uppercase font-mono">No files found here</div>`;
                    return;
                }

                itemList.forEach(item => {
                    const isStarred = item.starred ? 'text-yellow-400' : 'text-gray-400 hover:text-yellow-400';
                    const starIcon = `<button onclick="toggleStar('${item.id}', event)" class="${isStarred} p-1 transition relative z-20">
                        <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path></svg>
                    </button>`;

                    const ActionMenu = `
                        <div class="flex items-center gap-1.5 bg-black/60 backdrop-blur-md rounded-lg p-0.5 border border-white/10 relative z-20">
                            ${starIcon}
                            <button onclick="renameItem('${item.id}', '${item.name}', event)" class="text-gray-400 hover:text-white p-1 transition"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>
                            <button onclick="deleteItem('${item.id}', event)" class="text-gray-500 hover:text-rose-500 p-1 transition"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
                        </div>`;

                    if (item.type === 'folder') {
                        grid.innerHTML += `
                            <div class="glass p-3.5 rounded-2xl border border-white/5 flex flex-col justify-between h-32 relative hover:bg-white/5 transition group overflow-hidden">
                                <div onclick="navigateTo('${item.id}', '${item.name}')" class="absolute inset-0 cursor-pointer z-10"></div>
                                <div class="flex justify-between items-start">
                                    <svg class="w-8 h-8 text-indigo-400/80 group-hover:text-indigo-400 transition relative z-20" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                </div>
                                <span class="text-xs font-medium tracking-wide truncate w-full text-gray-300 pointer-events-none mb-1 relative z-20">${item.name}</span>
                                <div class="mt-1 self-end relative z-20">${ActionMenu}</div>
                            </div>`;
                    } else {
                        // Thumbnail Check
                        const ext = item.name.split('.').pop().toLowerCase();
                        let bgImageHTML = '';
                        if (['jpg','jpeg','png','webp','gif'].includes(ext)) {
                            // Streams the image silently behind the glass card
                            bgImageHTML = `<img src="/api/download/${item.id}" loading="lazy" class="absolute inset-0 w-full h-full object-cover opacity-40 group-hover:opacity-70 transition duration-300 pointer-events-none z-0">`;
                        }

                        grid.innerHTML += `
                            <div class="glass p-3.5 rounded-2xl border border-white/5 flex flex-col justify-between h-32 relative hover:bg-white/5 transition group overflow-hidden bg-black/40">
                                ${bgImageHTML}
                                <a href="/api/download/${item.id}" target="_blank" class="absolute inset-0 z-10"></a>
                                <div class="flex justify-between items-start">
                                    ${getFileBadge(item.name)}
                                </div>
                                <span class="text-xs font-medium truncate w-full text-gray-200 pointer-events-none mb-1 relative z-20 shadow-black drop-shadow-md">${item.name}</span>
                                <div class="mt-1 self-end relative z-20">${ActionMenu}</div>
                            </div>`;
                    }
                });
            }

            // NAVIGATION LOGIC
            function navigateTo(folderId, folderName) {
                // Delete any forward history if we are jumping to a new folder from the middle
                navStack = navStack.slice(0, navIndex + 1);
                
                navStack.push({id: folderId, name: folderName});
                navIndex++;
                currentFolder = folderId;
                updateBreadcrumbs();
                loadItems();
            }

            function jumpToRoot() {
                navStack = [{id: 'root', name: 'My Drive'}];
                navIndex = 0;
                currentFolder = 'root';
                updateBreadcrumbs();
                loadItems();
            }

            function navBack() {
                if (navIndex > 0) {
                    navIndex--;
                    currentFolder = navStack[navIndex].id;
                    updateBreadcrumbs();
                    loadItems();
                }
            }

            function navForward() {
                if (navIndex < navStack.length - 1) {
                    navIndex++;
                    currentFolder = navStack[navIndex].id;
                    updateBreadcrumbs();
                    loadItems();
                }
            }

            function updateBreadcrumbs() {
                const bc = document.getElementById('breadcrumbs');
                // Only show the active path up to current index
                const activePath = navStack.slice(0, navIndex + 1);
                
                bc.innerHTML = activePath.map((f, i) => {
                    const isLast = i === activePath.length - 1;
                    return `<span class="cursor-pointer px-1 py-0.5 rounded ${isLast ? 'text-violet-400 font-semibold bg-violet-500/10' : 'hover:text-gray-200 transition text-gray-500'}" 
                                  onclick="jumpToSpecificIndex(${i})">${f.name}</span>`;
                }).join(' <span class="text-gray-700">/</span> ');
            }

            function jumpToSpecificIndex(index) {
                navIndex = index;
                currentFolder = navStack[navIndex].id;
                updateBreadcrumbs();
                loadItems();
            }

            function filterByType(type) {
                activeTypeFilter = type;
                document.querySelectorAll('#typeFilters button').forEach(b => {
                    b.className = "glass px-4 py-2 rounded-lg font-medium text-gray-400 hover:text-white transition shrink-0";
                });
                document.getElementById(`filter-${type}`).className = "px-4 py-2 rounded-lg font-medium bg-violet-600 text-white transition shrink-0";
                loadItems();
            }

            async function createFolder() {
                const folderName = prompt("Enter new folder name:");
                if (!folderName) return;
                await fetch('/api/folders', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name: folderName, parent_id: currentFolder })
                });
                loadItems();
            }

            // PROGRESS BAR XHR UPLOAD ENGINE
            function uploadFile() {
                const input = document.getElementById('fileInput');
                if(input.files.length === 0) return;
                
                const file = input.files[0];
                const formData = new FormData();
                formData.append('file', file);
                formData.append('parent_id', currentFolder); 
                
                const progressContainer = document.getElementById('progressContainer');
                const progressBar = document.getElementById('progressBar');
                const progressPercent = document.getElementById('progressPercent');
                const progressText = document.getElementById('progressText');
                
                progressContainer.classList.remove('hidden');
                progressBar.style.width = '0%';
                progressPercent.innerText = '0%';
                progressText.innerText = `Uploading ${file.name}...`;

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/upload', true);

                xhr.upload.onprogress = function(e) {
                    if (e.lengthComputable) {
                        const percentComplete = Math.round((e.loaded / e.total) * 100);
                        progressBar.style.width = percentComplete + '%';
                        progressPercent.innerText = percentComplete + '%';
                    }
                };

                xhr.onload = function() {
                    progressContainer.classList.add('hidden');
                    input.value = ''; 
                    if (xhr.status === 200) {
                        loadItems();
                    } else {
                        alert("Upload failed. Ensure file size is reasonable for a free server pipeline.");
                    }
                };

                xhr.onerror = function() {
                    progressContainer.classList.add('hidden');
                    alert("A pipeline connection breakdown occurred during the transfer.");
                };

                xhr.send(formData);
            }

            async function toggleStar(id, event) {
                event.stopPropagation();
                event.preventDefault();
                await fetch(`/api/star/${id}`, { method: 'POST' });
                loadItems();
            }

            async function renameItem(id, currentName, event) {
                event.stopPropagation();
                event.preventDefault();
                const newName = prompt("Rename item:", currentName);
                if(!newName || newName === currentName) return;
                await fetch(`/api/rename/${id}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name: newName })
                });
                loadItems();
            }

            async function deleteItem(id, event) {
                event.stopPropagation();
                event.preventDefault();
                if(!confirm("Are you sure you want to permanently delete this item?")) return;
                await fetch(`/api/delete/${id}`, { method: 'DELETE' });
                loadItems();
            }

            loadItems();
        </script>
    </body>
    </html>
    """

# --- BACKEND API HANDLERS ---

class FolderRequest(BaseModel):
    name: str
    parent_id: str

class RenameRequest(BaseModel):
    name: str

@app.post("/api/folders")
async def create_new_folder(req: FolderRequest):
    folder_id = "fld_" + str(uuid.uuid4())[:8]
    vault_db[folder_id] = {
        "type": "folder",
        "name": req.name,
        "parent_id": req.parent_id,
        "tg_id": None,
        "starred": False
    }
    await save_db()
    return {"success": True}

@app.post("/api/upload")
async def upload_file(parent_id: str = Form(...), file: UploadFile = File(...)):
    if not BOT_TOKEN or not STORAGE_CHANNEL_ID:
        raise HTTPException(status_code=500, detail="Configuration properties missing.")
        
    file_bytes = await file.read()
    
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            telegram_url,
            data={"chat_id": STORAGE_CHANNEL_ID},
            files={"document": (file.filename, file_bytes)}
        )
        res_data = response.json()
        
    if not res_data.get("ok"):
        raise HTTPException(status_code=500, detail="Telegram cluster synchronization failed.")

    tg_file_id = res_data["result"]["document"]["file_id"]
    db_id = "doc_" + str(uuid.uuid4())[:8]
    
    vault_db[db_id] = {
        "type": "file",
        "name": file.filename, 
        "parent_id": parent_id,
        "tg_id": tg_file_id,
        "starred": False
    }
    await save_db()
    return {"success": True}

@app.get("/api/items")
async def get_items(parent_id: str = "root"):
    return {k: v for k, v in vault_db.items() if v.get("parent_id") == parent_id}

@app.post("/api/star/{item_id}")
async def toggle_star_item(item_id: str):
    if item_id in vault_db:
        vault_db[item_id]["starred"] = not vault_db[item_id].get("starred", False)
        await save_db()
    return {"success": True}

@app.post("/api/rename/{item_id}")
async def rename_item(item_id: str, req: RenameRequest):
    if item_id in vault_db:
        vault_db[item_id]["name"] = req.name
        await save_db()
    return {"success": True}

@app.delete("/api/delete/{item_id}")
async def delete_item(item_id: str):
    if item_id in vault_db:
        if vault_db[item_id]["type"] == "folder":
            for k, v in list(vault_db.items()):
                if v.get("parent_id") == item_id:
                    del vault_db[k]
        del vault_db[item_id]
        await save_db()
    return {"success": True}

@app.get("/api/download/{item_id}")
async def download_file(item_id: str):
    if item_id not in vault_db or vault_db[item_id]["type"] == "folder":
        raise HTTPException(status_code=404, detail="Requested file asset missing.")
    
    tg_id = vault_db[item_id]["tg_id"]
    async with httpx.AsyncClient() as client:
        info = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={tg_id}")
        file_path = info.json()["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return HTMLResponse(f"<script>window.location.href='{download_url}';</script>")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)

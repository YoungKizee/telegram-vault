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
            .loader { border-top-color: #8b5cf6; animation: spinner 0.6s linear infinite; }
            @keyframes spinner { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body class="p-4 max-w-3xl mx-auto pb-24">
        
        <div class="flex justify-between items-center mb-6">
            <div>
                <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 tracking-tight glow-text">SENZ1</h1>
            </div>
            <div class="text-xs px-3 py-1 rounded-full border border-emerald-500/30 text-emerald-400 font-mono bg-emerald-500/5">CLOUD SECURE</div>
        </div>

        <div id="uploadStatusPanel" class="hidden glass p-4 rounded-xl mb-4 border border-violet-500/20 flex items-center gap-3">
            <div class="loader ease-linear rounded-full border-2 border-t-2 border-gray-800 h-5 w-5"></div>
            <span id="statusMessage" class="text-xs font-mono tracking-wide text-violet-400">Processing secure cloud transmission...</span>
        </div>

        <div id="statsPanel" class="grid grid-cols-3 gap-3 mb-6 text-center text-xs">
            <div class="glass p-3 rounded-xl"><p class="text-gray-500 mb-0.5">Folders</p><span id="statFolders" class="text-base font-bold text-indigo-400">0</span></div>
            <div class="glass p-3 rounded-xl"><p class="text-gray-500 mb-0.5">Total Files</p><span id="statFiles" class="text-base font-bold text-cyan-400">0</span></div>
            <div class="glass p-3 rounded-xl"><p class="text-gray-500 mb-0.5">Starred</p><span id="statStarred" class="text-base font-bold text-fuchsia-400">0</span></div>
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

        <div class="flex justify-between items-center mb-4 px-1">
            <div class="flex items-center gap-3 text-xs text-gray-400">
                <div class="flex items-center gap-1">
                    <span>Sort:</span>
                    <select id="sortBy" onchange="loadItems()" class="bg-transparent border-none outline-none text-violet-400 font-medium cursor-pointer">
                        <option value="name-asc" class="bg-slate-950 text-white">Name (A-Z)</option>
                        <option value="name-desc" class="bg-slate-950 text-white">Name (Z-A)</option>
                        <option value="type" class="bg-slate-950 text-white">Item Type</option>
                    </select>
                </div>
            </div>
            <button onclick="toggleLayout()" id="layoutToggleBtn" class="text-gray-400 hover:text-white transition">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
            </button>
        </div>

        <div class="flex items-center gap-2 mb-4 text-xs font-medium px-1 bg-white/5 py-2 rounded-lg border border-white/5">
            <button onclick="navigateUpOneLevel()" class="p-1.5 rounded bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition flex items-center justify-center mr-1" title="Go back one folder">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7"></path></svg>
            </button>
            <div class="flex items-center gap-1.5 flex-wrap" id="breadcrumbs">
                <button onclick="navigateTo('root')" class="hover:text-violet-400 transition">My Drive</button>
            </div>
        </div>

        <div id="driveGrid" class="grid grid-cols-2 gap-3">
            </div>

        <script>
            let currentFolder = 'root';
            let folderHistory = [{id: 'root', name: 'My Drive'}];
            let activeTypeFilter = 'all';
            let currentViewLayout = 'grid'; 

            function getFileBadge(filename) {
                const ext = filename.split('.').pop().toLowerCase();
                let color = "bg-gray-500/10 text-gray-400 border-gray-500/20";
                
                if (['jpg','jpeg','png','gif','webp','svg'].includes(ext)) color = "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
                else if (['mp4','mkv','avi','mov'].includes(ext)) color = "bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20";
                else if (['mp3','wav','flac','ogg'].includes(ext)) color = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                else if (['pdf','doc','docx','txt','zip','rar','exe','msi'].includes(ext)) color = "bg-amber-500/10 text-amber-400 border-amber-500/20";
                
                return `<span class="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${color} font-mono">${ext}</span>`;
            }

            async function loadItems() {
                const res = await fetch(`/api/items?parent_id=${currentFolder}`);
                let items = await res.json();
                
                const searchQuery = document.getElementById('searchBar').value.toLowerCase();
                const sortBy = document.getElementById('sortBy').value;
                const grid = document.getElementById('driveGrid');
                
                grid.innerHTML = '';
                
                let folderCount = 0, fileCount = 0, starredCount = 0;
                Object.values(items).forEach(i => {
                    if(i.type === 'folder') folderCount++; else fileCount++;
                    if(i.starred) starredCount++;
                });
                document.getElementById('statFolders').innerText = folderCount;
                document.getElementById('statFiles').innerText = fileCount;
                document.getElementById('statStarred').innerText = starredCount;

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

                itemList.sort((a, b) => {
                    if (sortBy === 'name-asc') return a.name.localeCompare(b.name);
                    if (sortBy === 'name-desc') return b.name.localeCompare(a.name);
                    if (sortBy === 'type') return a.type.localeCompare(b.type);
                    return 0;
                });

                if (itemList.length === 0) {
                    grid.innerHTML = `<div class="col-span-full text-center py-16 text-gray-600 text-xs tracking-wider uppercase font-mono">No files found here</div>`;
                    return;
                }

                if (currentViewLayout === 'list') {
                    grid.className = "flex flex-col gap-2";
                } else {
                    grid.className = "grid grid-cols-2 gap-3";
                }

                itemList.forEach(item => {
                    const isStarred = item.starred ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-400';
                    const starIcon = `<button onclick="toggleStar('${item.id}', event)" class="${isStarred} p-1 transition relative z-20">
                        <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path></svg>
                    </button>`;

                    const ActionMenu = `
                        <div class="flex items-center gap-1.5 bg-black/40 rounded-lg p-0.5 border border-white/5 relative z-20">
                            ${starIcon}
                            <button onclick="renameItem('${item.id}', '${item.name}', event)" class="text-gray-500 hover:text-white p-1 transition"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>
                            ${item.type !== 'folder' ? `<button onclick="copyShareLink('${item.id}', event)" class="text-gray-500 hover:text-cyan-400 p-1 transition"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>` : ''}
                            <button onclick="deleteItem('${item.id}', event)" class="text-gray-600 hover:text-rose-500 p-1 transition"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
                        </div>`;

                    if (currentViewLayout === 'list') {
                        if (item.type === 'folder') {
                            grid.innerHTML += `
                                <div class="glass p-3 rounded-xl flex items-center justify-between border border-white/5 relative hover:bg-white/5 transition">
                                    <div onclick="navigateTo('${item.id}', '${item.name}')" class="flex items-center gap-3 flex-1 min-w-0 cursor-pointer">
                                        <svg class="w-6 h-6 text-indigo-400 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                        <span class="text-xs font-medium truncate pr-4 text-gray-300">${item.name}</span>
                                    </div>
                                    ${ActionMenu}
                                </div>`;
                        } else {
                            grid.innerHTML += `
                                <div class="glass p-3 rounded-xl flex items-center justify-between border border-white/5 relative hover:bg-white/5 transition">
                                    <a href="/api/download/${item.id}" target="_blank" class="flex items-center gap-3 flex-1 min-w-0">
                                        ${getFileBadge(item.name)}
                                        <span class="text-xs font-medium truncate pr-4 text-gray-400">${item.name}</span>
                                    </a>
                                    ${ActionMenu}
                                </div>`;
                        }
                    } else {
                        if (item.type === 'folder') {
                            grid.innerHTML += `
                                <div class="glass p-3.5 rounded-2xl border border-white/5 flex flex-col justify-between h-32 relative hover:bg-white/5 transition group">
                                    <div onclick="navigateTo('${item.id}', '${item.name}')" class="absolute inset-0 cursor-pointer z-10"></div>
                                    <div class="flex justify-between items-start">
                                        <svg class="w-8 h-8 text-indigo-400/80 group-hover:text-indigo-400 transition" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                    </div>
                                    <span class="text-xs font-medium tracking-wide truncate w-full text-gray-300 pointer-events-none mb-1">${item.name}</span>
                                    <div class="mt-1 self-end">${ActionMenu}</div>
                                </div>`;
                        } else {
                            grid.innerHTML += `
                                <div class="glass p-3.5 rounded-2xl border border-white/5 flex flex-col justify-between h-32 relative hover:bg-white/5 transition group">
                                    <a href="/api/download/${item.id}" target="_blank" class="absolute inset-0 z-10"></a>
                                    <div class="flex justify-between items-start">
                                        ${getFileBadge(item.name)}
                                    </div>
                                    <span class="text-xs font-medium truncate w-full text-gray-400 pointer-events-none mb-1">${item.name}</span>
                                    <div class="mt-1 self-end">${ActionMenu}</div>
                                </div>`;
                        }
                    }
                });
            }

            function navigateTo(folderId, folderName) {
                if (folderId === 'root') {
                    folderHistory = [{id: 'root', name: 'My Drive'}];
                } else {
                    const idx = folderHistory.findIndex(f => f.id === folderId);
                    if (idx !== -1) folderHistory = folderHistory.slice(0, idx + 1);
                    else folderHistory.push({id: folderId, name: folderName});
                }
                currentFolder = folderId;
                updateBreadcrumbs();
                loadItems();
            }

            function navigateUpOneLevel() {
                if (folderHistory.length <= 1) return; // Already at Root level
                folderHistory.pop();
                const parentFolder = folderHistory[folderHistory.length - 1];
                currentFolder = parentFolder.id;
                updateBreadcrumbs();
                loadItems();
            }

            function updateBreadcrumbs() {
                const bc = document.g

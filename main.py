import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import httpx

# 1. Production Configurations (Safely reads from Render Environment Settings)
BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID") 

app = FastAPI()
file_vault = {}  # Temporary storage tracker for your files

# 2. Creative Dashboard Frontend HTML
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vault UI</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 p-6 max-w-md mx-auto">
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-cyan-400">VaultOS v1.0</h1>
            <p class="text-xs text-slate-400">Custom Storage Interface</p>
        </div>

        <div class="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center bg-slate-800/50 hover:border-cyan-500 transition relative mb-6">
            <input type="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onchange="uploadFile()" />
            <p class="text-sm">Click or Drag & Drop a file here</p>
        </div>

        <h2 class="text-xs font-bold uppercase text-slate-500 tracking-wider mb-2">Your Cloud Files</h2>
        <div id="fileList" class="space-y-2"></div>

        <script>
            async function loadFiles() {
                const res = await fetch('/api/files');
                const data = await res.json();
                const list = document.getElementById('fileList');
                list.innerHTML = '';
                
                for (const [id, file] of Object.entries(data)) {
                    list.innerHTML += `
                        <div class="bg-slate-800 p-3 rounded-lg flex justify-between items-center">
                            <span class="text-sm truncate w-2/3">${file.filename}</span>
                            <a href="/api/download/${id}" target="_blank" class="bg-cyan-600 px-3 py-1 text-xs rounded hover:bg-cyan-500">Download</a>
                        </div>`;
                }
            }

            async function uploadFile() {
                const input = document.getElementById('fileInput');
                if(input.files.length === 0) return;
                
                const formData = new FormData();
                formData.append('file', input.files[0]);
                
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                if(res.ok) {
                    loadFiles();
                } else {
                    alert("Upload error encountered.");
                }
            }
            loadFiles();
        </script>
    </body>
    </html>
    """

# 3. File Upload Engine Pipeline
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not BOT_TOKEN or not STORAGE_CHANNEL_ID:
        raise HTTPException(status_code=500, detail="Server config keys missing on Render dashboard.")
        
    file_bytes = await file.read()
    
    # Send the raw file data straight into Telegram's storage cluster
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

    # Harvest Telegram's unique storage key for this file
    tg_file_id = res_data["result"]["document"]["file_id"]
    db_id = str(len(file_vault) + 1)
    
    # Store reference index securely mapping back to original file name
    file_vault[db_id] = {"filename": file.filename, "telegram_id": tg_file_id}
    return {"success": True, "id": db_id}

# 4. Storage Fetch Registry API
@app.get("/api/files")
async def get_files():
    return file_vault

# 5. File Download Direct Pipeline
@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    if file_id not in file_vault:
        raise HTTPException(status_code=404, detail="File index missing.")
    
    tg_id = file_vault[file_id]["telegram_id"]
    async with httpx.AsyncClient() as client:
        # Ask Telegram where the binary file is located
        info = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={tg_id}")
        file_path = info.json()["result"]["file_path"]
        
        # Build direct streaming download destination address link
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return HTMLResponse(f"<script>window.location.href='{download_url}';</script>")

if __name__ == "__main__":
    # Crucial adjustment: Render maps web projects directly via port 10000
    uvicorn.run("main:app", host="0.0.0.0", port=10000)

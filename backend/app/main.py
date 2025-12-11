from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI()

# Crucial for allowing Next.js on port 3000 to talk to FastAPI on port 8000
origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Backend running successfully!"}

@app.post("/analyze-history/")
async def analyze_history(stream_files: list[UploadFile] = File(...)):
    # In a real app, you'd process the files using Polars here.
    # For now, let's just confirm receipt.
    file_names = [file.filename for file in stream_files]
    return {
        "message": f"Successfully received {len(file_names)} files.",
        "files_received": file_names,
        "next_step": "Start Polars processing here!"
    }
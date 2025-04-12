import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as router_api
from app.pages.router import router as router_pages
from app.config import settings


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


app.mount("/files", StaticFiles(directory=settings.UPLOAD_DIR), name="files")
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


app.include_router(router_api)
app.include_router(router_pages)
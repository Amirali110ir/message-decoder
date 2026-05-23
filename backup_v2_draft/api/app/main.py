from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import admin, auth, contacts, decode, feedback, payments, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Message Decoder API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(user.router)
app.include_router(contacts.router)
app.include_router(decode.router)
app.include_router(payments.router)
app.include_router(feedback.router)
app.include_router(admin.router)

static_dir = Path(__file__).resolve().parents[2] / "web_static"
if not static_dir.exists():
    static_dir = Path(__file__).resolve().parents[1] / "web_static"
if static_dir.exists():
    next_static_dir = static_dir / "_next"
    if next_static_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(next_static_dir)), name="next-static")

    @app.get("/", include_in_schema=False)
    def web_index():
        return FileResponse(static_dir / "index.html")

    @app.get("/admin", include_in_schema=False)
    def web_admin():
        admin_index = static_dir / "admin" / "index.html"
        if admin_index.exists():
            return FileResponse(admin_index)
        return FileResponse(static_dir / "admin.html")

    @app.get("/{path:path}", include_in_schema=False)
    def web_asset(path: str):
        asset = static_dir / path
        if asset.exists() and asset.is_file():
            return FileResponse(asset)
        index_asset = asset / "index.html"
        if asset.exists() and asset.is_dir() and index_asset.exists():
            return FileResponse(index_asset)
        return FileResponse(static_dir / "404.html", status_code=404)

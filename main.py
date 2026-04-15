import logging
from dotenv import load_dotenv
load_dotenv()  # must be first — before any module reads os.getenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database import Base, engine, SessionLocal
from models import User
from auth import hash_password
from routes.auth import router as auth_router
from routes.assess import router as assess_router
from routes.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

Base.metadata.create_all(bind=engine)

# Seed admin user if not exists
def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@taiga.com").first():
            db.add(User(name="Admin", email="admin@taiga.com", hashed_password=hash_password("Admin@123"), role="admin"))
            db.commit()
    finally:
        db.close()

_seed_admin()

logger = logging.getLogger(__name__)
leash_key = os.getenv("LEASH_API_KEY", "")
logger.info("[ENV] LEASH_API_KEY: %s", leash_key[:8] + "..." if leash_key else "NOT SET ❌")

app = FastAPI(title="TAIGA Compliance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://control-tower-frontend.onrender.com"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(assess_router)
app.include_router(admin_router)

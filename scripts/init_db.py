"""
Database initialization and seeding script for Context Bank.
Usage:
    python scripts/init_db.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.database.connection import engine, Base, SessionLocal
from backend.database.models import User, Context, ContextTrigger
from backend.core.config import settings
from backend.api.auth import get_or_create_dev_user
from backend.context_bank.storage import ContextStorage
from backend.schemas.contexts import ContextCreate


def init_database():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("[OK] Schema initialized successfully.")

    db = SessionLocal()
    try:
        dev_user = get_or_create_dev_user(db)
        print(f"[OK] Default dev user confirmed: {dev_user.email} (ID: {dev_user.id})")

        # Check if VOXCENT context already exists
        existing = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == dev_user.id,
            ContextTrigger.trigger_word == "VOXCENT",
        ).first()

        if not existing:
            print("Seeding demo context: VOXCENT...")
            voxcent_data = ContextCreate(
                trigger_word="VOXCENT",
                alternative_triggers=["VC_APP", "VOXCENT_CORE"],
                title="Voxcent AI Learning and Career Assistant",
                summary="A voice-first AI application with five specialized roles and an independent Context Bank.",
                detailed_content="Voxcent assists learners and career transitioners with voice-driven guidance, interview prep, and progress tracking.",
                status="In Progress",
                category="Projects",
                tags=["voice", "assistant", "career", "fastapi", "pgvector"],
                important_decisions=[
                    {"text": "Context Bank is an independent subsystem.", "status": "confirmed"},
                    {"text": "Python is the primary programming language.", "status": "confirmed"},
                    {"text": "PostgreSQL is the persistent database with pgvector for semantic retrieval.", "status": "confirmed"},
                    {"text": "FastAPI powers the REST backend, Streamlit powers the UI.", "status": "confirmed"}
                ],
                completed_work=[
                    "Initial project specification defined.",
                    "Independent Context Bank architecture designed and implemented.",
                    "Trigger registry and exact retrieval engine built."
                ],
                open_questions=[
                    "External integration strategy and authentication details."
                ],
                next_steps=[
                    "Implement the core trigger registry.",
                    "Build context CRUD operations.",
                    "Integrate retrieval with a compatible AI client."
                ],
                privacy="private"
            )
            ContextStorage.create_context(db, dev_user.id, voxcent_data)
            db.commit()
            print("[OK] Seeded VOXCENT context successfully!")

        print("\nDatabase initialization complete! You can now start the application.")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()

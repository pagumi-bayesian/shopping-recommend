import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound
import asyncio
# import aiofiles # Unused import removed
import logging # Use logging for better output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Cloud Storage設定
BUCKET_NAME = os.getenv("STORAGE_BUCKET", "shopping-app-sqlite-db")
DB_FILE_NAME = os.getenv("DB_FILE_NAME", "shopping_app.db")
# Use /tmp explicitly for Cloud Run compatibility
LOCAL_DB_PATH = f"/tmp/{DB_FILE_NAME}"

# Cloud Storageクライアント (Initialize later if needed, or ensure credentials available)
try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(DB_FILE_NAME)
except Exception as e:
    logger.error(f"Failed to initialize Google Cloud Storage client: {e}. Database persistence might fail.")
    storage_client = None
    bucket = None
    blob = None

# 非同期でDBファイルをダウンロード (アプリケーション起動時に呼び出す)
async def download_db_file_async():
    if storage_client is None or blob is None:
        logger.error("Storage client not initialized. Skipping DB download.")
        return

    # Check if file already exists locally (e.g., container reuse)
    if os.path.exists(LOCAL_DB_PATH):
         logger.info(f"DB file already exists locally at {LOCAL_DB_PATH}. Skipping download.")
         return

    logger.info(f"Attempting to download DB file from gs://{BUCKET_NAME}/{DB_FILE_NAME} to {LOCAL_DB_PATH}")
    try:
        # Use asyncio.to_thread for blocking I/O
        await asyncio.to_thread(blob.download_to_filename, LOCAL_DB_PATH)
        logger.info(f"DB file downloaded successfully to {LOCAL_DB_PATH}")
    except NotFound:
         logger.warning(f"DB file not found in Cloud Storage (gs://{BUCKET_NAME}/{DB_FILE_NAME}). Assuming first run or no existing data. A new DB will be created locally.")
         # Ensure the /tmp directory exists if needed (usually does in Cloud Run)
         os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    except Exception as e:
        logger.error(f"Error downloading DB file: {e}", exc_info=True)
        # Decide if the app should proceed without the DB or raise an error

# 非同期でDBファイルをアップロード (アプリケーション終了時に呼び出す)
async def upload_db_file_async():
    if storage_client is None or blob is None:
        logger.error("Storage client not initialized. Skipping DB upload.")
        return

    if not os.path.exists(LOCAL_DB_PATH):
        logger.warning(f"Local DB file {LOCAL_DB_PATH} not found. Skipping upload.")
        return

    logger.info(f"Attempting to upload DB file from {LOCAL_DB_PATH} to gs://{BUCKET_NAME}/{DB_FILE_NAME}")
    try:
        # Use asyncio.to_thread for blocking I/O
        await asyncio.to_thread(blob.upload_from_filename, LOCAL_DB_PATH)
        logger.info(f"DB file uploaded successfully.")
    except Exception as e:
        logger.error(f"Error uploading DB file: {e}", exc_info=True)


# SQLite接続URL
DATABASE_URL = f"sqlite+aiosqlite:///{LOCAL_DB_PATH}"
logger.info(f"Database URL configured: {DATABASE_URL}")

# エンジン作成
# Consider adding pool_size and max_overflow if needed, though less critical for SQLite
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Set to True for debugging SQL
    connect_args={"check_same_thread": False}  # Required for SQLite with threads/asyncio
)

# セッションメーカー
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

# モデルベース
Base = declarative_base()

# 非同期データベースセッションを取得するための依存性関数
async def get_db():
    """
    Provides an asynchronous database session.
    Upload is now handled by application lifespan events.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Error during DB session: {e}", exc_info=True)
            # Consider rolling back the session here if applicable
            # await session.rollback()
            raise
        # Removed upload_db_file() call from here

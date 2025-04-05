import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv() # .envファイルから環境変数を読み込む

# --- 環境変数から接続情報を取得 ---
# ローカル開発用にデフォルト値を設定（.envファイルでの上書きを推奨）
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_local_dev_password") # 必ず.env等で設定してください
DB_HOST = os.getenv("DB_HOST", "localhost") # ローカル開発時はlocalhost (Proxy経由) or Public IP
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres") # デフォルトDBを使用

# --- Cloud SQL接続用の特別な考慮 (GCP環境) ---
# Cloud RunなどのGCP環境では、インスタンス接続名を使ったUnixソケット接続が推奨される
# 例: shopping-app-455905:asia-northeast1:shopping-app-db
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

if INSTANCE_CONNECTION_NAME:
    # Unixソケット接続 (Cloud Runなど)
    # パスワードはURLエンコードが必要な場合があるため注意
    # (asyncpgは自動で処理してくれることが多い)
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
else:
    # TCP接続 (ローカル開発、Cloud SQL Proxyなど)
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SQLAlchemy非同期エンジンを作成 ---
# echo=Trueにすると実行されるSQLがログに出力される（デバッグ時に便利）
engine = create_async_engine(DATABASE_URL, echo=False)

# --- 非同期データベースセッションを作成するためのクラス ---
# expire_on_commit=False は非同期コードで推奨される設定
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

# --- モデルクラス（後でmodels.pyで定義）のベースとなるクラス ---
Base = declarative_base()

# --- 非同期データベースセッションを取得するための依存性関数 ---
async def get_db():
    """
    非同期データベースセッションを提供する依存性関数
    """
    async with AsyncSessionLocal() as session:
        yield session

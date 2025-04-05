import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine # 同期エンジン作成用
from sqlalchemy import pool

from alembic import context

# --- モデル定義の読み込み設定 ---
# backendディレクトリをPythonパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# backend/models.py から Base をインポート
try:
    from models import Base
except ImportError:
    # もし backend/database.py から Base をインポートしている場合はこちら
    # from database import Base
    print("Could not import Base from models. Trying database.")
    try:
        from database import Base
    except ImportError:
        raise ImportError("Could not import Base from models.py or database.py. Check import paths.")

# Alembic Configオブジェクト
config = context.config

# Pythonロギングの設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# モデルのMetaDataオブジェクトを設定
# target_metadata = None # 元の行
target_metadata = Base.metadata

# --- .env ファイルの読み込み設定 ---
# alembicコマンド実行時に .env を読み込むようにする
from dotenv import load_dotenv
# alembic ディレクトリの一つ上の階層 (backend) にある .env を探す
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    print(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f".env file not found at: {dotenv_path}. Using system environment variables.")

# --- データベース接続URLの取得 ---
# alembic.ini の sqlalchemy.url よりも環境変数を優先する
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD") # .envから読み込む想定、デフォルトなし
DB_HOST = os.getenv("DB_HOST", "127.0.0.1") # Cloud SQL Proxy想定
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

if DB_PASSWORD is None:
    raise ValueError("DB_PASSWORD environment variable not set. Please configure it in your .env file or environment.")

# Alembic用の同期接続URL (psycopg2を使用)
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# configオブジェクトにも設定しておく (run_migrations_offline で使われる可能性のため)
config.set_main_option('sqlalchemy.url', DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # ここでは config から URL を取得する
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # 型の比較を有効化
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # ここでは環境変数から構築したURLで同期エンジンを作成
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True, # 型の比較を有効化
            # include_schemas=True # マルチスキーマの場合に必要
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

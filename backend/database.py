from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# docker-compose.ymlのenvironmentで設定したDATABASE_URLを取得
# 環境変数が設定されていなければデフォルトでローカルのSQLiteファイルを使用
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# SQLAlchemyエンジンを作成
# connect_argsはSQLite使用時のみ必要（FastAPIの複数スレッドからのアクセスに対応）
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# データベースセッションを作成するためのクラス
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルクラス（後でmodels.pyで定義）のベースとなるクラス
Base = declarative_base()

# --- データベースセッションを取得するための依存性関数 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

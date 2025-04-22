import os
import sys
import csv
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
# backendディレクトリを直接インポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

# モデルを直接インポート
try:
    # backend.models ではなく models を直接インポート
    from models import Base, User, Product, PurchaseHistory
    print("Models imported successfully.")
except ImportError as e:
    print(f"Error importing models: {e}")
    print("Current directory:", current_dir)
    print("Backend directory:", backend_dir)
    print("Python path:", sys.path)
    print("Checking if models.py exists:", os.path.exists(os.path.join(backend_dir, 'models.py')))
    exit(1)
    exit(1)

# SQLiteデータベースへの接続 (alembic.iniで指定したパス)
# このスクリプト実行前に alembic upgrade head でDBファイルが作成されている前提
DATABASE_URL = "sqlite:///backend/shopping_app.db" # backend ディレクトリ内のDBファイルを指定
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# CSVファイルのパス (プロジェクトルートからの相対パス)
DATA_DIR = './data_export' # データエクスポート先ディレクトリ
USERS_CSV = f'{DATA_DIR}/users.csv'
PRODUCTS_CSV = f'{DATA_DIR}/products.csv'
PURCHASE_HISTORY_CSV = f'{DATA_DIR}/purchase_history.csv'

def import_users(db_session):
    print("Importing users...")
    try:
        with open(USERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # gcloud sql export csv はデフォルトでヘッダーなし
            # next(reader) # ヘッダー行をスキップしない
            count = 0
            for row in reader:
                if len(row) != 3:
                    print(f"Warning: Skipping invalid user row: {row}")
                    continue
                user_id, name, preferences_str = row
                try:
                    # 空文字列や 'null' 文字列の場合を考慮
                    preferences = json.loads(preferences_str) if preferences_str and preferences_str.lower() != 'null' else None
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse preferences for user {user_id}: {preferences_str}")
                    preferences = None
                user = User(id=int(user_id), name=name, preferences=preferences)
                db_session.merge(user) # 既存IDがあれば更新、なければ挿入
                count += 1
        db_session.commit()
        print(f"{count} users imported.")
    except FileNotFoundError:
        print(f"Error: {USERS_CSV} not found. Please export data first.")
    except Exception as e:
        print(f"Error importing users: {e}")
        db_session.rollback()
        raise # エラーを再送出して処理を中断

def import_products(db_session):
    print("Importing products...")
    try:
        with open(PRODUCTS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # next(reader) # ヘッダー行をスキップしない
            count = 0
            for row in reader:
                if len(row) != 5:
                    print(f"Warning: Skipping invalid product row: {row}")
                    continue
                product_id, name, category, typical_price_str, seasonality = row
                # 空文字列の場合を考慮
                typical_price = float(typical_price_str) if typical_price_str else None
                product = Product(
                    id=int(product_id),
                    name=name,
                    category=category,
                    typical_price=typical_price,
                    seasonality=seasonality
                )
                db_session.merge(product)
                count += 1
        db_session.commit()
        print(f"{count} products imported.")
    except FileNotFoundError:
        print(f"Error: {PRODUCTS_CSV} not found. Please export data first.")
    except Exception as e:
        print(f"Error importing products: {e}")
        db_session.rollback()
        raise

def import_purchase_history(db_session):
    print("Importing purchase history...")
    try:
        with open(PURCHASE_HISTORY_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # next(reader) # ヘッダー行をスキップしない
            count = 0
            for row in reader:
                if len(row) != 4:
                    print(f"Warning: Skipping invalid purchase history row: {row}")
                    continue
                history_id, user_id, product_id, purchase_date_str = row
                try:
                    # 日付形式に合わせてパース (例: 'YYYY-MM-DD')
                    purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"Warning: Could not parse date for history {history_id}: {purchase_date_str}")
                    continue # 日付が無効な場合はスキップ

                history = PurchaseHistory(
                    id=int(history_id),
                    user_id=int(user_id),
                    product_id=int(product_id),
                    purchase_date=purchase_date
                )
                db_session.merge(history)
                count += 1
        db_session.commit()
        print(f"{count} purchase history records imported.")
    except FileNotFoundError:
        print(f"Error: {PURCHASE_HISTORY_CSV} not found. Please export data first.")
    except Exception as e:
        print(f"Error importing purchase history: {e}")
        db_session.rollback()
        raise

if __name__ == "__main__":
    # データエクスポートディレクトリが存在するか確認
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data export directory '{DATA_DIR}' not found.")
        print("Please run the gcloud export commands first and place CSV files in this directory.")
        exit(1)

    db = SessionLocal()
    try:
        print("Starting data import...")
        # 外部キー制約のため、UserとProductを先にインポート
        import_users(db)
        import_products(db)
        import_purchase_history(db)
        print("\nData import completed successfully!")
        print(f"Data imported into: {DATABASE_URL}")
        print("Please verify the data using a tool like DB Browser for SQLite.")
        print(f"Next step: Upload '{os.path.basename(DATABASE_URL)}' to your Cloud Storage bucket.")
    except Exception as e:
        print(f"\nAn error occurred during data import: {e}")
        print("Import process stopped.")
    finally:
        db.close()

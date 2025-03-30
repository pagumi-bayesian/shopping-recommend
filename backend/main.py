from fastapi import FastAPI, Depends, HTTPException # Depends, HTTPException を追加
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session # Session を追加
from fastapi.middleware.cors import CORSMiddleware # CORSミドルウェアをインポート

# ローカルモジュールを絶対インポート
import models
import database
import crud
import schemas
import llm_interface # 追加: LLM連携モジュール
from datetime import date # 追加: date型のため

# .envファイルから環境変数を読み込む（将来のAPIキー用）
load_dotenv()

# --- データベーステーブル作成 ---
# アプリケーション起動時にモデルに基づいてテーブルを作成する
models.Base.metadata.create_all(bind=database.engine)
# -----------------------------

app = FastAPI(
    title="Shopping Recommendation API",
    description="API for suggesting items to buy.",
    version="0.1.0",
)

# --- CORSミドルウェアの設定 ---
origins = [
    "http://localhost:5173", # フロントエンドの開発サーバー
    # 必要に応じて他のオリジンも追加
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # 許可するオリジン
    allow_credentials=True,
    allow_methods=["*"], # すべてのHTTPメソッドを許可
    allow_headers=["*"], # すべてのHTTPヘッダーを許可
)
# -----------------------------

@app.get("/")
async def read_root():
    """
    ヘルスチェック用エンドポイント
    """
    return {"message": "Shopping Recommendation API is running!"}

# --- ここから下にAPIエンドポイントを追加していく ---

@app.post("/purchase/", response_model=schemas.PurchaseHistory)
async def create_purchase(purchase: schemas.PurchaseHistoryCreate, db: Session = Depends(database.get_db)):
    """
    新しい購入履歴を登録する
    """
    # 簡単のため、ユーザーと商品が存在するかチェック (本来はもっと厳密に)
    db_user = crud.get_user(db, user_id=purchase.user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_product = crud.get_product(db, product_id=purchase.product_id)
    if db_product is None:
        # 商品が存在しない場合は、ここで作成するかエラーにするか選択
        # ここでは仮にエラーとする
        raise HTTPException(status_code=404, detail="Product not found")
        # もし自動作成する場合:
        # product_data = schemas.ProductCreate(name="Unknown Product") # 仮の商品情報
        # db_product = crud.create_product(db=db, product=product_data)
        # purchase.product_id = db_product.id # 新しいIDをセット

    return crud.create_purchase_history(db=db, purchase=purchase)

@app.get("/history/{user_id}", response_model=list[schemas.PurchaseHistory])
async def read_purchase_history(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    指定されたユーザーの購入履歴を取得する
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    history = crud.get_purchase_history(db, user_id=user_id, skip=skip, limit=limit)
    return history

# --- ユーザー作成エンドポイント (テスト用) ---
@app.post("/users/", response_model=schemas.User)
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_name(db, name=user.name)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

# --- ユーザー検索エンドポイント ---
@app.get("/users/search", response_model=list[schemas.User])
def search_users_endpoint(q: str = "", db: Session = Depends(database.get_db)):
    """
    クエリ文字列に名前が部分一致するユーザーを検索する
    """
    if not q:
        return [] # クエリが空なら空リストを返す
    users = crud.search_users_by_name(db=db, query=q)
    return users

# --- 商品作成エンドポイント (テスト用) ---
@app.post("/products/", response_model=schemas.Product)
def create_product_endpoint(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    # 簡単のため、同名商品の重複チェックは省略
    return crud.create_product(db=db, product=product)

# --- 商品検索エンドポイント ---
@app.get("/products/search", response_model=list[schemas.Product])
def search_products_endpoint(q: str = "", db: Session = Depends(database.get_db)):
    """
    クエリ文字列に名前が部分一致する商品を検索する
    """
    if not q:
        return [] # クエリが空なら空リストを返す
    products = crud.search_products_by_name(db=db, query=q)
    return products

# --- ヘルパー関数: 現在の季節を取得 ---
def get_current_season() -> str:
    """現在の月を基に季節を返す"""
    month = date.today().month
    if month in [3, 4, 5]:
        return "春"
    elif month in [6, 7, 8]:
        return "夏"
    elif month in [9, 10, 11]:
        return "秋"
    else: # 12, 1, 2
        return "冬"

# --- 商品提案エンドポイント ---
@app.get("/suggest/{user_id}", response_model=schemas.SuggestionResponse)
async def suggest_items_endpoint(user_id: int, db: Session = Depends(database.get_db)):
    """
    指定されたユーザーにおすすめの商品をLLMを使って提案する
    """
    # ユーザー存在チェック
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 購入履歴を取得
    history_orm = crud.get_purchase_history(db, user_id=user_id, limit=20) # 直近20件を取得
    # PurchaseHistoryオブジェクトを辞書のリストに変換 (Pydanticモデル経由)
    # 注意: from_ormを使うには、schemas.PurchaseHistoryのConfigにorm_mode=Trueが必要 (既に追加済み)
    history_dict = [schemas.PurchaseHistory.from_orm(item).dict() for item in history_orm]


    # 現在の季節を取得
    current_season = get_current_season()

    # LLMへのプロンプトを作成
    history_text = llm_interface.format_purchase_history_for_prompt(history_dict)
    prompt = f"""ユーザーID {user_id} の購入履歴と現在の季節情報に基づいて、おすすめの商品を5つ提案してください。
提案は具体的な商品名を挙げ、なぜそれをおすすめするのか簡単な理由も添えてください。
定番だけでなく、少し意外性のある商品も混ぜてください。

{history_text}

現在の季節は「{current_season}」です。

提案リスト:
"""

    # LLMから提案を生成
    suggestion_text = llm_interface.generate_suggestions(prompt)

    if not suggestion_text:
        raise HTTPException(status_code=500, detail="Failed to generate suggestions from LLM.")

    # (オプション) 提案内容をDBに保存する処理をここに追加可能

    return schemas.SuggestionResponse(suggestions_text=suggestion_text)


# 例: 商品提案エンドポイント (将来実装)
# @app.post("/suggest")
# async def suggest_items(user_id: int):
#     # ... 提案ロジック ...
#     return {"suggestions": []}

# 例: 購入履歴登録エンドポイント (将来実装)
# @app.post("/purchase")
# async def record_purchase(purchase_data: dict):
#     # ... 登録ロジック ...
#     return {"status": "success"}

# -------------------------------------------------

if __name__ == "__main__":
    # このファイルが直接実行された場合の処理 (通常はuvicorn経由で実行)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

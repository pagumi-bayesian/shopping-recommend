from fastapi import FastAPI, Depends, HTTPException
import os
from dotenv import load_dotenv
# from sqlalchemy.orm import Session # 削除
from sqlalchemy.ext.asyncio import AsyncSession # 追加: 非同期セッション
from fastapi.middleware.cors import CORSMiddleware

# ローカルモジュールを絶対インポート
import models
import database
import crud
import schemas
import llm_interface
from datetime import date

# .envファイルから環境変数を読み込む
load_dotenv()

# --- データベーステーブル作成 ---
# アプリケーション起動時にモデルに基づいてテーブルを作成する
# models.Base.metadata.create_all(bind=database.engine) # 非同期エンジンでは直接実行できないためコメントアウト。マイグレーションツール(Alembic等)の使用を推奨。
# -----------------------------

app = FastAPI(
    title="Shopping Recommendation API",
    description="API for suggesting items to buy.",
    version="0.1.0",
)

# --- CORSミドルウェアの設定 ---
origins = [
    "http://localhost:5173", # フロントエンドの開発サーバー
    "http://localhost", # Firebase Hostingローカルエミュレータ用など
    "https://shopping-app-455905.web.app", # デプロイされたフロントエンドURL
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
async def create_purchase(purchase: schemas.PurchaseHistoryCreate, db: AsyncSession = Depends(database.get_db)): # Session -> AsyncSession
    """
    新しい購入履歴を登録する
    """
    # ユーザーと商品が存在するかチェック
    db_user = await crud.get_user(db, user_id=purchase.user_id) # await 追加
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_product = await crud.get_product(db, product_id=purchase.product_id) # await 追加
    if db_product is None:
        # 商品が存在しない場合はエラー
        raise HTTPException(status_code=404, detail="Product not found")

    # crud.create_purchase_history は Pydantic モデルを返すのでそのまま return
    return await crud.create_purchase_history(db=db, purchase=purchase) # await 追加

@app.get("/history/{user_id}", response_model=list[schemas.PurchaseHistory])
async def read_purchase_history(user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)): # Session -> AsyncSession
    """
    指定されたユーザーの購入履歴を取得する
    """
    db_user = await crud.get_user(db, user_id=user_id) # await 追加
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    history = await crud.get_purchase_history(db, user_id=user_id, skip=skip, limit=limit) # await 追加
    # history は ORM オブジェクトのリスト。Pydanticがレスポンスモデルに合わせて自動変換
    return history

# --- ユーザー作成エンドポイント (テスト用) ---
@app.post("/users/", response_model=schemas.User)
async def create_user_endpoint(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)): # def -> async def, Session -> AsyncSession
    """新しいユーザーを作成する"""
    db_user = await crud.get_user_by_name(db, name=user.name) # await 追加
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await crud.create_user(db=db, user=user) # await 追加

# --- ユーザー検索エンドポイント ---
@app.get("/users/search", response_model=list[schemas.User])
async def search_users_endpoint(q: str = "", db: AsyncSession = Depends(database.get_db)): # def -> async def, Session -> AsyncSession
    """
    クエリ文字列に名前が部分一致するユーザーを検索する
    """
    if not q:
        return []
    users = await crud.search_users_by_name(db=db, query=q) # await 追加
    return users

# --- 商品作成エンドポイント (テスト用) ---
@app.post("/products/", response_model=schemas.Product)
async def create_product_endpoint(product: schemas.ProductCreate, db: AsyncSession = Depends(database.get_db)): # def -> async def, Session -> AsyncSession
    """新しい商品を作成する"""
    # 簡単のため、同名商品の重複チェックは省略
    return await crud.create_product(db=db, product=product) # await 追加

# --- 商品検索エンドポイント ---
@app.get("/products/search", response_model=list[schemas.Product])
async def search_products_endpoint(q: str = "", db: AsyncSession = Depends(database.get_db)): # def -> async def, Session -> AsyncSession
    """
    クエリ文字列に名前が部分一致する商品を検索する
    """
    if not q:
        return []
    products = await crud.search_products_by_name(db=db, query=q) # await 追加
    return products

# --- ヘルパー関数: 現在の季節を取得 ---
# DBアクセス不要なので同期関数のまま
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
async def suggest_items_endpoint(user_id: int, db: AsyncSession = Depends(database.get_db)): # Session -> AsyncSession
    """
    指定されたユーザーにおすすめの商品をLLMを使って提案する
    """
    # ユーザー存在チェック
    db_user = await crud.get_user(db, user_id=user_id) # await 追加
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 購入履歴を取得
    history_orm = await crud.get_purchase_history(db, user_id=user_id, limit=20) # await 追加

    # PurchaseHistoryオブジェクトを辞書のリストに変換 (Pydanticモデル経由)
    # Pydantic V2 を想定: model_validate と model_dump
    try:
        # mode='json' は datetime オブジェクトなどをISO形式文字列に変換する
        history_dict = [schemas.PurchaseHistory.model_validate(item).model_dump(mode='json') for item in history_orm]
    except AttributeError: # Pydantic V1 fallback
        # V1 の from_orm はネストしたリレーションを自動で読み込まない場合があるため注意
        # crud側で selectinload しているので大丈夫なはず
        history_dict = [schemas.PurchaseHistory.from_orm(item).dict() for item in history_orm]


    # 現在の季節を取得
    # current_season = get_current_season()

    # LLMへのプロンプトを作成
    # llm_interface.format_purchase_history_for_prompt は history_dict を受け取るように修正が必要かもしれない
    history_text = llm_interface.format_purchase_history_for_prompt(history_dict) # 辞書リストを渡す
    prompt = f"""以下が、ユーザーID {user_id}がこれまでに購入した食品の履歴です。
この履歴を参考にして、次回購入すべき食品を提案してください。

{history_text}
"""

    # LLMから提案を生成 (llm_interface.py内の関数が同期的なのでawait不要)
    suggestion_text = llm_interface.generate_suggestions(user_prompt=prompt) # 引数名を user_prompt に変更

    if not suggestion_text:
        raise HTTPException(status_code=500, detail="Failed to generate suggestions from LLM.")

    # (オプション) 提案内容をDBに保存する処理をここに追加可能 (非同期で)

    return schemas.SuggestionResponse(suggestions_text=suggestion_text)


# -------------------------------------------------

if __name__ == "__main__":
    # このファイルが直接実行された場合の処理 (通常はuvicorn経由で実行)
    # ローカルでのデバッグ実行用
    import uvicorn
    # この場合、.envファイルが読み込まれる想定
    print("Running uvicorn for local development...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

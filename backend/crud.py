from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select # select をインポート
from sqlalchemy.orm import selectinload # selectinload をインポート
import models
import schemas

# --- User CRUD ---
async def get_user(db: AsyncSession, user_id: int) -> models.User | None:
    """指定されたIDのユーザーを取得する"""
    statement = select(models.User).where(models.User.id == user_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none() # 1件取得、なければNone

async def get_user_by_name(db: AsyncSession, name: str) -> models.User | None:
    """指定された名前のユーザーを取得する"""
    statement = select(models.User).where(models.User.name == name)
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """新しいユーザーを作成する"""
    # Pydantic v2 を想定 (v1なら .dict())
    try:
        user_data = user.model_dump()
    except AttributeError:
        user_data = user.dict()
    db_user = models.User(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def search_users_by_name(db: AsyncSession, query: str, limit: int = 10) -> list[models.User]:
    """指定された文字列を名前に含むユーザーを検索する (部分一致、大文字小文字区別なし)"""
    search = f"%{query}%"
    statement = select(models.User).where(models.User.name.ilike(search)).limit(limit)
    result = await db.execute(statement)
    return result.scalars().all() # 複数件取得

# --- Product CRUD ---
async def get_product(db: AsyncSession, product_id: int) -> models.Product | None:
    """指定されたIDの商品を取得する"""
    statement = select(models.Product).where(models.Product.id == product_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def create_product(db: AsyncSession, product: schemas.ProductCreate) -> models.Product:
    """新しい商品を作成する"""
    try:
        product_data = product.model_dump()
    except AttributeError:
        product_data = product.dict()
    db_product = models.Product(**product_data)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def search_products_by_name(db: AsyncSession, query: str, limit: int = 10) -> list[models.Product]:
    """指定された文字列を名前に含む商品を検索する (部分一致、大文字小文字区別なし)"""
    search = f"%{query}%"
    statement = select(models.Product).where(models.Product.name.ilike(search)).limit(limit)
    result = await db.execute(statement)
    return result.scalars().all()

# --- PurchaseHistory CRUD ---
async def create_purchase_history(db: AsyncSession, purchase: schemas.PurchaseHistoryCreate) -> models.PurchaseHistory:
    """購入履歴をデータベースに登録する"""
    try:
        # スキーマに quantity がないことを想定
        purchase_data = purchase.model_dump()
    except AttributeError:
        purchase_data = purchase.dict()
    db_purchase = models.PurchaseHistory(**purchase_data)
    db.add(db_purchase)
    await db.commit()
    await db.refresh(db_purchase)
    # 関連オブジェクトをリフレッシュ後に読み込む (任意だが役立つ場合がある)
    await db.refresh(db_purchase, attribute_names=['product', 'owner'])
    return db_purchase

async def get_purchase_history(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[models.PurchaseHistory]:
    """指定されたユーザーの購入履歴を取得する (商品情報も含む)"""
    statement = (
        select(models.PurchaseHistory)
        .options(selectinload(models.PurchaseHistory.product)) # Eager loading
        .where(models.PurchaseHistory.user_id == user_id)
        .order_by(models.PurchaseHistory.purchase_date.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(statement)
    return result.scalars().all()

# --- Suggestion CRUD ---
# (将来実装)

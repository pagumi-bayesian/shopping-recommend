from sqlalchemy.orm import Session, joinedload  # joinedload をインポート
import models
import schemas  # 同階層のmodelsとschemasをインポート


# --- User CRUD ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_name(db: Session, name: str):
    return db.query(models.User).filter(models.User.name == name).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(name=user.name, preferences=user.preferences)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def search_users_by_name(db: Session, query: str, limit: int = 10):
    """
    指定された文字列を名前に含むユーザーを検索する (部分一致、大文字小文字区別なし)
    """
    search = f"%{query}%"
    return (
        db.query(models.User).filter(models.User.name.ilike(search)).limit(limit).all()
    )


# --- Product CRUD ---
# (必要に応じて実装)
def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def search_products_by_name(db: Session, query: str, limit: int = 10):
    """
    指定された文字列を名前に含む商品を検索する (部分一致、大文字小文字区別なし)
    """
    search = f"%{query}%"
    return (
        db.query(models.Product)
        .filter(models.Product.name.ilike(search))
        .limit(limit)
        .all()
    )


# --- PurchaseHistory CRUD ---
def create_purchase_history(db: Session, purchase: schemas.PurchaseHistoryCreate):
    """
    購入履歴をデータベースに登録する
    """
    db_purchase = models.PurchaseHistory(
        user_id=purchase.user_id,
        product_id=purchase.product_id,
        purchase_date=purchase.purchase_date,
        # quantity=purchase.quantity, # 削除
    )
    db.add(db_purchase)
    db.commit()  # データベースに変更をコミット
    db.refresh(db_purchase)  # 登録されたデータを再読み込み（IDなどが確定する）
    return db_purchase


def get_purchase_history(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """
    指定されたユーザーの購入履歴を取得する (商品情報も含む)
    """
    return (
        db.query(models.PurchaseHistory)
        .options(
            joinedload(models.PurchaseHistory.product)
        )  # ProductをJOINして読み込む
        .filter(models.PurchaseHistory.user_id == user_id)
        .order_by(models.PurchaseHistory.purchase_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Suggestion CRUD ---
# (将来実装)

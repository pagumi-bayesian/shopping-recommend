from pydantic import BaseModel
from datetime import date
from typing import Optional

# --- Product スキーマ ---
class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    typical_price: Optional[float] = None
    seasonality: Optional[str] = None

class ProductCreate(ProductBase):
    pass # ProductBaseと同じ

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True # orm_mode から変更

# --- User スキーマ ---
class UserBase(BaseModel):
    name: str
    preferences: Optional[dict] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    # purchase_history: list['PurchaseHistory'] = [] # 必要に応じて追加
    # suggestions: list['Suggestion'] = [] # 必要に応じて追加

    class Config:
        from_attributes = True # orm_mode から変更

# --- PurchaseHistory スキーマ ---
class PurchaseHistoryBase(BaseModel):
    product_id: int
    purchase_date: date
    # quantity: Optional[int] = 1 # 削除

class PurchaseHistoryCreate(PurchaseHistoryBase):
    user_id: int # 登録時にはユーザーIDが必要

class PurchaseHistory(PurchaseHistoryBase):
    id: int
    user_id: int
    # owner: User # 必要に応じて関連モデルの情報を含める
    product: Product # 商品情報を含めるように変更

    class Config:
        from_attributes = True # orm_mode から変更

# --- Suggestion スキーマ ---
# (将来実装: DB保存用)
# class SuggestionBase(BaseModel):
#     user_id: int
#     product_id: int
#     suggestion_date: date
#     reason: Optional[str] = None

# class SuggestionCreate(SuggestionBase):
#     pass

# class Suggestion(SuggestionBase):
#     id: int
#     was_purchased: bool

#     class Config:
#         orm_mode = True

# --- APIレスポンス用スキーマ ---
class SuggestionResponse(BaseModel):
    """商品提案APIのレスポンス"""
    suggestions_text: str # LLMが生成した提案テキスト

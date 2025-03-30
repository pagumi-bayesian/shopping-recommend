from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base # database.pyで定義したBaseクラスをインポート

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # 簡単のため名前をユニークとする
    preferences = Column(JSON) # 好みなどをJSON形式で保存

    purchase_history = relationship("PurchaseHistory", back_populates="owner")
    suggestions = relationship("Suggestion", back_populates="user")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    typical_price = Column(Float)
    seasonality = Column(String) # 例: "夏", "冬", "通年" など

    purchase_history = relationship("PurchaseHistory", back_populates="product")
    suggestions = relationship("Suggestion", back_populates="product")

class PurchaseHistory(Base):
    __tablename__ = "purchase_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    purchase_date = Column(Date)
    # quantity = Column(Integer, default=1) # 削除

    owner = relationship("User", back_populates="purchase_history")
    product = relationship("Product", back_populates="purchase_history")

class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    suggestion_date = Column(Date)
    reason = Column(String) # なぜ提案されたかの理由
    was_purchased = Column(Boolean, default=False) # 提案された商品が実際に購入されたか

    user = relationship("User", back_populates="suggestions")
    product = relationship("Product", back_populates="suggestions")

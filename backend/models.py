import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # queued | running | complete | failed
    url_count: Mapped[int] = mapped_column(Integer, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    in_scope: Mapped[int] = mapped_column(Integer, default=0)
    excluded: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    products: Mapped[list["Product"]] = relationship("Product", back_populates="job")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ingredients_raw: Mapped[str] = mapped_column(Text, nullable=False)
    in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scope_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="products")
    product_ingredients: Mapped[list["ProductIngredient"]] = relationship(
        "ProductIngredient", back_populates="product"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    internal_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    is_dye_active: Mapped[bool] = mapped_column(Boolean, default=False)

    product_ingredients: Mapped[list["ProductIngredient"]] = relationship(
        "ProductIngredient", back_populates="ingredient"
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"

    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id"), primary_key=True
    )
    component: Mapped[str] = mapped_column(String(500), nullable=False)
    is_dye_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="product_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="product_ingredients")

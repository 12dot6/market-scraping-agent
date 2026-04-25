from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Product, ProductIngredient
from backend.schemas import IngredientItem, ProductResult

router = APIRouter(prefix="/api/jobs", tags=["results"])


@router.get("/{job_id}/products", response_model=list[ProductResult])
def get_products(job_id: str, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(Product.job_id == job_id)
        .options(
            joinedload(Product.product_ingredients).joinedload(ProductIngredient.ingredient)
        )
        .all()
    )
    result = []
    for p in products:
        ingredients = [
            IngredientItem(
                name=pi.ingredient.name,
                internal_name=pi.ingredient.internal_name,
                component=pi.component,
                is_dye_active=pi.is_dye_active,
            )
            for pi in p.product_ingredients
        ]
        result.append(
            ProductResult(
                id=p.id,
                url=p.url,
                name=p.name,
                in_scope=p.in_scope,
                scope_reason=p.scope_reason,
                ingredients=ingredients,
                error=p.error,
            )
        )
    return result

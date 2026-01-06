from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.services.auth import get_current_user
from app.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductStatus,
    CannabisMetafields,
)

router = APIRouter(prefix="/products", tags=["Products"])

# In-memory product storage (will be replaced with Supabase)
products_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[ProductResponse])
async def get_products(
    store_id: Optional[str] = None,
    status: Optional[ProductStatus] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get all products for the current user."""
    products = list(products_db.values())

    # Filter by store_id if provided
    if store_id:
        products = [p for p in products if p.get("store_id") == store_id]

    # Filter by status
    if status:
        products = [p for p in products if p.get("status") == status]

    # Search by title
    if search:
        search_lower = search.lower()
        products = [p for p in products if search_lower in p.get("title", "").lower()]

    # Paginate
    total = len(products)
    products = products[offset:offset + limit]

    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific product."""
    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return products_db[product_id]


@router.post("", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new product."""
    product_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    product_data = {
        "id": product_id,
        "store_id": product.store_id,
        "shopify_product_id": product.shopify_product_id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "compare_at_price": product.compare_at_price,
        "sku": product.sku,
        "barcode": product.barcode,
        "inventory_quantity": product.inventory_quantity,
        "images": product.images,
        "tags": product.tags,
        "product_type": product.product_type,
        "vendor": product.vendor,
        "status": ProductStatus.DRAFT,
        "cannabis_metafields": product.cannabis_metafields.model_dump() if product.cannabis_metafields else None,
        "ai_description_generated": False,
        "synced_to_shopify": False,
        "created_at": now,
        "updated_at": now,
    }

    products_db[product_id] = product_data
    return product_data


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a product."""
    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    product = products_db[product_id]

    # Update fields that were provided
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "cannabis_metafields" and value:
            product[field] = value if isinstance(value, dict) else value.model_dump()
        else:
            product[field] = value

    product["updated_at"] = datetime.utcnow().isoformat()
    products_db[product_id] = product

    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a product."""
    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    del products_db[product_id]
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/generate-description")
async def generate_product_description(
    product_id: str,
    tone: str = Query(default="professional"),
    length: str = Query(default="medium"),
    current_user: dict = Depends(get_current_user)
):
    """Generate AI description for a product."""
    from app.services.openai_service import openai_service

    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    product = products_db[product_id]
    cannabis_meta = product.get("cannabis_metafields") or {}

    description = await openai_service.generate_product_description(
        product_name=product["title"],
        product_type=product.get("product_type"),
        strain_type=cannabis_meta.get("strain_type"),
        thc_percentage=cannabis_meta.get("thc_percentage"),
        cbd_percentage=cannabis_meta.get("cbd_percentage"),
        terpenes=cannabis_meta.get("terpenes"),
        effects=cannabis_meta.get("effects"),
        flavors=cannabis_meta.get("flavors"),
        tone=tone,
        length=length,
    )

    # Update the product with generated description
    products_db[product_id]["description"] = description
    products_db[product_id]["ai_description_generated"] = True
    products_db[product_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "product_id": product_id,
        "description": description,
        "ai_generated": True
    }


@router.post("/bulk-import")
async def bulk_import_products(
    products: List[ProductCreate],
    current_user: dict = Depends(get_current_user)
):
    """Bulk import products."""
    created = []
    errors = []

    for i, product in enumerate(products):
        try:
            product_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            product_data = {
                "id": product_id,
                "store_id": product.store_id,
                "shopify_product_id": product.shopify_product_id,
                "title": product.title,
                "description": product.description,
                "price": product.price,
                "compare_at_price": product.compare_at_price,
                "sku": product.sku,
                "barcode": product.barcode,
                "inventory_quantity": product.inventory_quantity,
                "images": product.images,
                "tags": product.tags,
                "product_type": product.product_type,
                "vendor": product.vendor,
                "status": ProductStatus.DRAFT,
                "cannabis_metafields": product.cannabis_metafields.model_dump() if product.cannabis_metafields else None,
                "ai_description_generated": False,
                "synced_to_shopify": False,
                "created_at": now,
                "updated_at": now,
            }

            products_db[product_id] = product_data
            created.append(product_data)
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    return {
        "created": len(created),
        "errors": errors,
        "products": created
    }

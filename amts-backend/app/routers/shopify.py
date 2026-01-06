from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import secrets

from app.services.auth import get_current_user
from app.services.shopify import ShopifyService, get_shopify_service, store_connections
from app.config import settings

router = APIRouter(prefix="/shopify", tags=["Shopify Integration"])

# In-memory store storage (will be replaced with Supabase)
stores_db: Dict[str, Dict[str, Any]] = {}
oauth_states: Dict[str, Dict[str, Any]] = {}


@router.get("/auth/install")
async def install_app(
    shop: str,
    current_user: dict = Depends(get_current_user)
):
    """Initiate Shopify OAuth flow."""
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "user_id": current_user["id"],
        "shop": shop,
        "created_at": datetime.utcnow().isoformat()
    }

    # Build redirect URI
    redirect_uri = f"{settings.shopify_app_url}/api/shopify/auth/callback"

    shopify = ShopifyService(shop)
    auth_url = shopify.get_oauth_url(redirect_uri, state)

    return {"auth_url": auth_url}


@router.get("/auth/callback")
async def oauth_callback(
    code: str,
    shop: str,
    state: str,
    hmac: Optional[str] = None
):
    """Handle Shopify OAuth callback."""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    oauth_data = oauth_states.pop(state)
    user_id = oauth_data["user_id"]

    # Exchange code for access token
    shopify = ShopifyService(shop)
    try:
        token_data = await shopify.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {str(e)}"
        )

    # Create or update store record
    store_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Check if store already exists
    existing_store = None
    for sid, store in stores_db.items():
        if store["shopify_domain"] == shop:
            existing_store = sid
            break

    if existing_store:
        stores_db[existing_store]["shopify_access_token"] = access_token
        stores_db[existing_store]["status"] = "connected"
        stores_db[existing_store]["updated_at"] = now
        store_id = existing_store
    else:
        # Get shop info
        shopify.access_token = access_token
        shop_info = await shopify.get_shop()
        shop_data = shop_info.get("shop", {})

        stores_db[store_id] = {
            "id": store_id,
            "user_id": user_id,
            "name": shop_data.get("name", shop),
            "shopify_domain": shop,
            "shopify_access_token": access_token,
            "status": "connected",
            "industry": None,
            "brand_colors": None,
            "logo_url": None,
            "products_count": shop_data.get("products_count", 0),
            "last_synced": None,
            "created_at": now,
            "updated_at": now,
        }

    # Store connection for future use
    store_connections[shop] = ShopifyService(shop, access_token)

    # Redirect to frontend
    return RedirectResponse(url=f"{settings.cors_origins_list[0]}/dashboard/shopify?connected=true")


@router.get("/stores")
async def get_stores(
    current_user: dict = Depends(get_current_user)
):
    """Get all connected stores for the current user."""
    user_stores = [
        {k: v for k, v in store.items() if k != "shopify_access_token"}
        for store in stores_db.values()
        if store.get("user_id") == current_user["id"]
    ]
    return user_stores


@router.get("/stores/{store_id}")
async def get_store(
    store_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific store."""
    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    store = stores_db[store_id]
    if store.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return {k: v for k, v in store.items() if k != "shopify_access_token"}


@router.delete("/stores/{store_id}")
async def disconnect_store(
    store_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect a Shopify store."""
    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    store = stores_db[store_id]
    if store.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Remove from connections
    shop_domain = store.get("shopify_domain")
    if shop_domain in store_connections:
        del store_connections[shop_domain]

    del stores_db[store_id]
    return {"message": "Store disconnected successfully"}


@router.get("/stores/{store_id}/products")
async def get_store_products(
    store_id: str,
    limit: int = Query(default=50, le=250),
    page_info: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Fetch products from Shopify store."""
    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    store = stores_db[store_id]
    if store.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    shop_domain = store.get("shopify_domain")
    access_token = store.get("shopify_access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store not connected"
        )

    shopify = get_shopify_service(shop_domain, access_token)
    products = await shopify.get_products(limit, page_info)

    return products


@router.post("/stores/{store_id}/sync")
async def sync_store_products(
    store_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Sync products from Shopify to local database."""
    from app.routers.products import products_db

    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    store = stores_db[store_id]
    if store.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    shop_domain = store.get("shopify_domain")
    access_token = store.get("shopify_access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store not connected"
        )

    shopify = get_shopify_service(shop_domain, access_token)

    synced = 0
    errors = []

    try:
        products_response = await shopify.get_products(limit=250)
        shopify_products = products_response.get("products", [])

        for sp in shopify_products:
            try:
                product_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()

                # Find existing product by Shopify ID
                existing_id = None
                for pid, prod in products_db.items():
                    if prod.get("shopify_product_id") == str(sp["id"]):
                        existing_id = pid
                        break

                product_data = {
                    "id": existing_id or product_id,
                    "store_id": store_id,
                    "shopify_product_id": str(sp["id"]),
                    "title": sp.get("title", ""),
                    "description": sp.get("body_html", ""),
                    "price": float(sp.get("variants", [{}])[0].get("price", 0)),
                    "compare_at_price": float(sp.get("variants", [{}])[0].get("compare_at_price", 0) or 0),
                    "sku": sp.get("variants", [{}])[0].get("sku"),
                    "barcode": sp.get("variants", [{}])[0].get("barcode"),
                    "inventory_quantity": sp.get("variants", [{}])[0].get("inventory_quantity", 0),
                    "images": [img.get("src") for img in sp.get("images", [])],
                    "tags": sp.get("tags", "").split(", ") if sp.get("tags") else [],
                    "product_type": sp.get("product_type"),
                    "vendor": sp.get("vendor"),
                    "status": "active" if sp.get("status") == "active" else "draft",
                    "cannabis_metafields": None,
                    "ai_description_generated": False,
                    "synced_to_shopify": True,
                    "created_at": existing_id and products_db.get(existing_id, {}).get("created_at") or now,
                    "updated_at": now,
                }

                products_db[existing_id or product_id] = product_data
                synced += 1

            except Exception as e:
                errors.append({"product_id": sp.get("id"), "error": str(e)})

        # Update store sync time
        stores_db[store_id]["last_synced"] = datetime.utcnow().isoformat()
        stores_db[store_id]["products_count"] = synced

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )

    return {
        "synced": synced,
        "errors": errors,
        "last_synced": stores_db[store_id]["last_synced"]
    }


@router.post("/stores/{store_id}/export/{product_id}")
async def export_product_to_shopify(
    store_id: str,
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Export a local product to Shopify."""
    from app.routers.products import products_db

    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    store = stores_db[store_id]
    product = products_db[product_id]

    if store.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    shop_domain = store.get("shopify_domain")
    access_token = store.get("shopify_access_token")

    shopify = get_shopify_service(shop_domain, access_token)

    # Build Shopify product data
    shopify_product = {
        "title": product["title"],
        "body_html": product.get("description", ""),
        "vendor": product.get("vendor", ""),
        "product_type": product.get("product_type", ""),
        "tags": ", ".join(product.get("tags", [])),
        "variants": [{
            "price": str(product["price"]),
            "compare_at_price": str(product.get("compare_at_price", "")) if product.get("compare_at_price") else None,
            "sku": product.get("sku", ""),
            "barcode": product.get("barcode", ""),
            "inventory_quantity": product.get("inventory_quantity", 0),
        }],
    }

    # Add images if present
    if product.get("images"):
        shopify_product["images"] = [{"src": url} for url in product["images"]]

    try:
        if product.get("shopify_product_id"):
            # Update existing
            result = await shopify.update_product(product["shopify_product_id"], shopify_product)
        else:
            # Create new
            result = await shopify.create_product(shopify_product)
            products_db[product_id]["shopify_product_id"] = str(result["product"]["id"])

        products_db[product_id]["synced_to_shopify"] = True
        products_db[product_id]["updated_at"] = datetime.utcnow().isoformat()

        return {
            "success": True,
            "shopify_product_id": products_db[product_id]["shopify_product_id"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

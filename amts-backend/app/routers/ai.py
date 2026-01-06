from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json

from app.services.auth import get_current_user
from app.services.openai_service import openai_service

router = APIRouter(prefix="/ai", tags=["AI Content Generation"])


class GenerateDescriptionRequest(BaseModel):
    product_name: str
    product_type: Optional[str] = None
    brand: Optional[str] = None
    strain_type: Optional[str] = None
    thc_percentage: Optional[float] = None
    cbd_percentage: Optional[float] = None
    terpenes: Optional[List[str]] = None
    effects: Optional[List[str]] = None
    flavors: Optional[List[str]] = None
    tone: str = "professional"
    length: str = "medium"


class SEORequest(BaseModel):
    product_name: str
    description: str


@router.post("/generate-description")
async def generate_description(
    request: GenerateDescriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI product description."""
    description = await openai_service.generate_product_description(
        product_name=request.product_name,
        product_type=request.product_type,
        brand=request.brand,
        strain_type=request.strain_type,
        thc_percentage=request.thc_percentage,
        cbd_percentage=request.cbd_percentage,
        terpenes=request.terpenes,
        effects=request.effects,
        flavors=request.flavors,
        tone=request.tone,
        length=request.length,
    )

    return {
        "description": description,
        "ai_generated": True,
        "tone": request.tone,
        "length": request.length,
    }


@router.post("/generate-description/stream")
async def generate_description_stream(
    request: GenerateDescriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stream AI product description generation."""

    async def stream_generator():
        async for chunk in openai_service.generate_product_description_stream(
            product_name=request.product_name,
            product_type=request.product_type,
            brand=request.brand,
            strain_type=request.strain_type,
            thc_percentage=request.thc_percentage,
            cbd_percentage=request.cbd_percentage,
            terpenes=request.terpenes,
            effects=request.effects,
            flavors=request.flavors,
            tone=request.tone,
            length=request.length,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/generate-seo")
async def generate_seo(
    request: SEORequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate SEO meta content."""
    seo_content = await openai_service.generate_seo_content(
        product_name=request.product_name,
        description=request.description,
    )

    return seo_content


@router.post("/bulk-generate")
async def bulk_generate_descriptions(
    product_ids: List[str],
    tone: str = Query(default="professional"),
    length: str = Query(default="medium"),
    current_user: dict = Depends(get_current_user)
):
    """Bulk generate descriptions for multiple products."""
    from app.routers.products import products_db
    from datetime import datetime

    results = []
    errors = []

    for product_id in product_ids:
        if product_id not in products_db:
            errors.append({"product_id": product_id, "error": "Product not found"})
            continue

        product = products_db[product_id]
        cannabis_meta = product.get("cannabis_metafields") or {}

        try:
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

            products_db[product_id]["description"] = description
            products_db[product_id]["ai_description_generated"] = True
            products_db[product_id]["updated_at"] = datetime.utcnow().isoformat()

            results.append({
                "product_id": product_id,
                "title": product["title"],
                "description": description,
            })

        except Exception as e:
            errors.append({"product_id": product_id, "error": str(e)})

    return {
        "generated": len(results),
        "errors": errors,
        "results": results,
    }


@router.get("/usage")
async def get_usage(
    current_user: dict = Depends(get_current_user)
):
    """Get AI generation usage statistics."""
    # In production, this would query the database
    # For now, return mock data
    return {
        "user_id": current_user["id"],
        "tier": current_user.get("subscription_tier", "free"),
        "generations_used": 5,
        "generations_limit": 10,
        "remaining": 5,
        "reset_date": "2025-02-01",
    }

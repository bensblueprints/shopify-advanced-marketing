from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class StrainType(str, Enum):
    INDICA = "indica"
    SATIVA = "sativa"
    HYBRID = "hybrid"
    CBD = "cbd"


class CannabisMetafields(BaseModel):
    strain_type: Optional[StrainType] = None
    thc_percentage: Optional[float] = None
    cbd_percentage: Optional[float] = None
    terpenes: Optional[List[str]] = None
    effects: Optional[List[str]] = None
    flavors: Optional[List[str]] = None
    grow_method: Optional[str] = None
    lineage: Optional[str] = None
    lab_tested: Optional[bool] = None
    lab_results_url: Optional[str] = None


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    inventory_quantity: int = 0
    images: List[str] = []
    tags: List[str] = []
    product_type: Optional[str] = None
    vendor: Optional[str] = None


class ProductCreate(ProductBase):
    store_id: str
    shopify_product_id: Optional[str] = None
    cannabis_metafields: Optional[CannabisMetafields] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    inventory_quantity: Optional[int] = None
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[ProductStatus] = None
    cannabis_metafields: Optional[CannabisMetafields] = None


class Product(ProductBase):
    id: str
    store_id: str
    shopify_product_id: Optional[str] = None
    status: ProductStatus = ProductStatus.DRAFT
    cannabis_metafields: Optional[CannabisMetafields] = None
    ai_description_generated: bool = False
    synced_to_shopify: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: str
    store_id: str
    shopify_product_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    inventory_quantity: int
    images: List[str]
    tags: List[str]
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: ProductStatus
    cannabis_metafields: Optional[CannabisMetafields] = None
    ai_description_generated: bool
    synced_to_shopify: bool
    created_at: datetime

    class Config:
        from_attributes = True

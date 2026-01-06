import httpx
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
from app.config import settings


class ShopifyService:
    """Service for interacting with Shopify API."""

    API_VERSION = "2024-01"

    def __init__(self, shop_domain: str, access_token: Optional[str] = None):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/{self.API_VERSION}"

    def get_oauth_url(self, redirect_uri: str, state: str) -> str:
        """Generate OAuth authorization URL."""
        params = {
            "client_id": settings.shopify_api_key,
            "scope": settings.shopify_scopes,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"https://{self.shop_domain}/admin/oauth/authorize?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        url = f"https://{self.shop_domain}/admin/oauth/access_token"
        payload = {
            "client_id": settings.shopify_api_key,
            "client_secret": settings.shopify_api_secret,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def verify_webhook(self, data: bytes, hmac_header: str) -> bool:
        """Verify Shopify webhook signature."""
        digest = hmac.new(
            settings.shopify_api_secret.encode("utf-8"),
            data,
            hashlib.sha256
        ).digest()
        computed_hmac = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(computed_hmac, hmac_header)

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Shopify API."""
        if not self.access_token:
            raise ValueError("Access token required for API requests")

        url = f"{self.base_url}/{endpoint}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def get_shop(self) -> Dict[str, Any]:
        """Get shop information."""
        return await self._request("GET", "shop.json")

    async def get_products(
        self,
        limit: int = 50,
        page_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get products from Shopify store."""
        params = {"limit": limit}
        if page_info:
            params["page_info"] = page_info
        return await self._request("GET", "products.json", params=params)

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get a single product."""
        return await self._request("GET", f"products/{product_id}.json")

    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product."""
        return await self._request("POST", "products.json", data={"product": product_data})

    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing product."""
        return await self._request("PUT", f"products/{product_id}.json", data={"product": product_data})

    async def delete_product(self, product_id: str) -> None:
        """Delete a product."""
        await self._request("DELETE", f"products/{product_id}.json")

    async def get_themes(self) -> Dict[str, Any]:
        """Get all themes."""
        return await self._request("GET", "themes.json")

    async def get_theme_assets(self, theme_id: str) -> Dict[str, Any]:
        """Get theme assets."""
        return await self._request("GET", f"themes/{theme_id}/assets.json")

    async def update_theme_asset(
        self,
        theme_id: str,
        key: str,
        value: str
    ) -> Dict[str, Any]:
        """Update a theme asset."""
        return await self._request(
            "PUT",
            f"themes/{theme_id}/assets.json",
            data={"asset": {"key": key, "value": value}}
        )

    async def get_metafields(
        self,
        owner_resource: str,
        owner_id: str
    ) -> Dict[str, Any]:
        """Get metafields for a resource."""
        return await self._request(
            "GET",
            f"{owner_resource}/{owner_id}/metafields.json"
        )

    async def create_metafield(
        self,
        owner_resource: str,
        owner_id: str,
        namespace: str,
        key: str,
        value: Any,
        value_type: str = "string"
    ) -> Dict[str, Any]:
        """Create a metafield."""
        return await self._request(
            "POST",
            f"{owner_resource}/{owner_id}/metafields.json",
            data={
                "metafield": {
                    "namespace": namespace,
                    "key": key,
                    "value": value,
                    "type": value_type,
                }
            }
        )


# Store connections in memory (will be replaced with database)
store_connections: Dict[str, ShopifyService] = {}


def get_shopify_service(shop_domain: str, access_token: Optional[str] = None) -> ShopifyService:
    """Get or create a Shopify service instance."""
    if shop_domain in store_connections:
        return store_connections[shop_domain]

    service = ShopifyService(shop_domain, access_token)
    if access_token:
        store_connections[shop_domain] = service
    return service

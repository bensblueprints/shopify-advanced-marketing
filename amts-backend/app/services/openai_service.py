from openai import AsyncOpenAI
from typing import Optional, Dict, Any, List, AsyncGenerator
from app.config import settings


class OpenAIService:
    """Service for AI content generation using OpenAI."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate_product_description(
        self,
        product_name: str,
        product_type: Optional[str] = None,
        brand: Optional[str] = None,
        strain_type: Optional[str] = None,
        thc_percentage: Optional[float] = None,
        cbd_percentage: Optional[float] = None,
        terpenes: Optional[List[str]] = None,
        effects: Optional[List[str]] = None,
        flavors: Optional[List[str]] = None,
        tone: str = "professional",
        length: str = "medium",
    ) -> str:
        """Generate an AI product description for cannabis products."""

        if not self.client:
            return self._generate_mock_description(product_name, strain_type)

        # Build context for the AI
        context_parts = [f"Product: {product_name}"]

        if product_type:
            context_parts.append(f"Type: {product_type}")
        if brand:
            context_parts.append(f"Brand: {brand}")
        if strain_type:
            context_parts.append(f"Strain Type: {strain_type}")
        if thc_percentage:
            context_parts.append(f"THC: {thc_percentage}%")
        if cbd_percentage:
            context_parts.append(f"CBD: {cbd_percentage}%")
        if terpenes:
            context_parts.append(f"Terpenes: {', '.join(terpenes)}")
        if effects:
            context_parts.append(f"Effects: {', '.join(effects)}")
        if flavors:
            context_parts.append(f"Flavors: {', '.join(flavors)}")

        context = "\n".join(context_parts)

        length_guide = {
            "short": "2-3 sentences",
            "medium": "1-2 paragraphs",
            "long": "3-4 paragraphs with detailed information"
        }

        tone_guide = {
            "professional": "professional and informative",
            "casual": "casual and approachable",
            "luxury": "sophisticated and premium",
            "educational": "educational and detailed"
        }

        prompt = f"""Write a compelling product description for a cannabis product.

Product Information:
{context}

Guidelines:
- Tone: {tone_guide.get(tone, 'professional')}
- Length: {length_guide.get(length, '1-2 paragraphs')}
- Focus on the unique qualities and benefits
- Include sensory details about aroma and flavor if applicable
- Mention the effects and use cases
- Be compliant with cannabis marketing regulations (no health claims)
- Do not use terms like "cure", "treat", or make medical claims

Write an engaging description that would appeal to cannabis consumers."""

        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert cannabis copywriter who creates compelling, compliant product descriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
        )

        return response.choices[0].message.content

    async def generate_product_description_stream(
        self,
        product_name: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream product description generation."""

        if not self.client:
            # Mock streaming for development
            mock_text = self._generate_mock_description(product_name, kwargs.get("strain_type"))
            for word in mock_text.split():
                yield word + " "
            return

        # Build the same prompt as above
        context_parts = [f"Product: {product_name}"]
        for key, value in kwargs.items():
            if value and key not in ["tone", "length"]:
                if isinstance(value, list):
                    context_parts.append(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
                else:
                    context_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        context = "\n".join(context_parts)
        tone = kwargs.get("tone", "professional")
        length = kwargs.get("length", "medium")

        prompt = f"""Write a compelling product description for a cannabis product.

Product Information:
{context}

Write an engaging, {tone} description in {length} length."""

        stream = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert cannabis copywriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_seo_content(
        self,
        product_name: str,
        description: str,
    ) -> Dict[str, str]:
        """Generate SEO meta title and description."""

        if not self.client:
            return {
                "meta_title": f"{product_name} | Premium Cannabis",
                "meta_description": f"Shop {product_name} - premium quality cannabis products. Fast delivery, lab tested."
            }

        prompt = f"""Generate SEO optimized meta content for this cannabis product:

Product: {product_name}
Description: {description}

Provide:
1. Meta Title (50-60 characters)
2. Meta Description (150-160 characters)

Format your response as:
META_TITLE: [title]
META_DESCRIPTION: [description]"""

        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200,
        )

        content = response.choices[0].message.content

        # Parse the response
        meta_title = ""
        meta_description = ""

        for line in content.split("\n"):
            if line.startswith("META_TITLE:"):
                meta_title = line.replace("META_TITLE:", "").strip()
            elif line.startswith("META_DESCRIPTION:"):
                meta_description = line.replace("META_DESCRIPTION:", "").strip()

        return {
            "meta_title": meta_title,
            "meta_description": meta_description
        }

    def _generate_mock_description(self, product_name: str, strain_type: Optional[str] = None) -> str:
        """Generate a mock description for development without API key."""
        strain_descriptions = {
            "indica": "Known for its deeply relaxing effects, this indica-dominant strain offers a calming experience perfect for unwinding after a long day. With earthy undertones and a smooth finish, it's ideal for evening use.",
            "sativa": "This uplifting sativa strain delivers an energizing experience that sparks creativity and focus. Featuring bright citrus notes and a euphoric onset, it's perfect for daytime activities and social gatherings.",
            "hybrid": "A perfectly balanced hybrid that offers the best of both worlds - the uplifting energy of sativa combined with the relaxing body effects of indica. Expect a well-rounded experience with complex flavor profiles.",
            "cbd": "This CBD-rich strain provides therapeutic benefits without intense psychoactive effects. Perfect for those seeking relief while maintaining clarity and focus throughout their day."
        }

        base_desc = strain_descriptions.get(
            strain_type.lower() if strain_type else "hybrid",
            strain_descriptions["hybrid"]
        )

        return f"{product_name}\n\n{base_desc}\n\nExperience the quality difference with our carefully cultivated products, rigorously tested for purity and potency."


# Singleton instance
openai_service = OpenAIService()

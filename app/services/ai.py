import json
import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class AIService:

    async def suggest_aliases(self, url: str, count: int = 5) -> list[str]:
        """
        Generate meaningful short URL aliases from a long URL.
        Example: https://amazon.com/product/iphone-15 → ['iphone-15', 'apple-phone', 'iphone-deal']
        """
        prompt = f"""
        Given this URL: {url}

        Generate {count} short, memorable URL aliases that:
        - Are 2-4 words max, hyphen separated
        - Clearly describe the content
        - Are URL-safe (only letters, numbers, hyphens)
        - Are concise and easy to remember

        Return ONLY a JSON array of strings, no explanation.
        Example: ["iphone-deal", "apple-phone", "iphone-15-pro"]
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150,
            )

            content = response.choices[0].message.content.strip()
            suggestions = json.loads(content)

            # Sanitize — ensure URL safe
            clean = [
                s.lower().replace(" ", "-")
                for s in suggestions
                if isinstance(s, str)
            ]
            return clean[:count]

        except Exception as e:
            logger.error(f"AI alias suggestion failed: {e}")
            raise ValueError(f"AI service error: {str(e)}")

    async def check_malicious(self, url: str) -> dict:
        """
        Analyze a URL for phishing/malicious indicators.
        Returns confidence level and reasons.
        """
        prompt = f"""
        Analyze this URL for signs of being malicious, phishing, or spam: {url}

        Check for:
        - Suspicious domain patterns (typosquatting, random chars)
        - Known phishing patterns
        - Suspicious TLDs or subdomains
        - URL obfuscation techniques
        - Misleading brand impersonation

        Return ONLY a JSON object with this exact structure:
        {{
            "is_malicious": true/false,
            "confidence": "low/medium/high",
            "reasons": ["reason1", "reason2"],
            "recommendation": "brief recommendation"
        }}
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300,
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result

        except Exception as e:
            logger.error(f"AI malicious check failed: {e}")
            raise ValueError(f"AI service error: {str(e)}")

    async def generate_utm_tags(self, url: str, campaign_goal: str) -> dict:
        """
        Generate UTM campaign parameters for marketing tracking.
        Example: goal="product launch" → utm_source, utm_medium, utm_campaign etc.
        """
        prompt = f"""
        Generate UTM tracking parameters for this URL: {url}
        Campaign goal: {campaign_goal}

        Return ONLY a JSON object with this exact structure:
        {{
            "utm_source": "value",
            "utm_medium": "value",
            "utm_campaign": "value",
            "utm_content": "value",
            "utm_term": "value",
            "explanation": "brief explanation of choices"
        }}

        Make values lowercase, hyphen-separated, relevant to the campaign goal.
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=300,
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result

        except Exception as e:
            logger.error(f"AI UTM generation failed: {e}")
            raise ValueError(f"AI service error: {str(e)}")
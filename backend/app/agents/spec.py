"""Spec agent: business model, financial outline, PRD, and tech TZ."""

from typing import Any

from openai import AsyncOpenAI

from app.agents.markdown_sections import split_fenced_sections
from app.core.config import Settings, settings


class SpecAgent:
    """Draft product and delivery specs from prior launch research."""

    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        config: Settings = settings,
    ) -> None:
        self.client = client
        self.config = config

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        completion = await self.client.chat.completions.create(
            model=self.config.openrouter_model,
            temperature=0.35,
            max_completion_tokens=3_200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Norma AI Spec Agent. Draft four markdown sections "
                        "for a launch strategy pack.\n"
                        "Rules:\n"
                        "- Stay consistent with research, competitors, positioning, "
                        "roadmap, and marketing notes.\n"
                        "- Financial section: order-of-magnitude unit economics and "
                        "ranges only; never invent precise live market figures.\n"
                        "- Tech TZ should be practical for a modern SaaS/agent stack "
                        "(APIs, data, auth, RAG) when relevant.\n"
                        "- Mark unverified claims as **Assumption**.\n"
                        "- Respond with exactly four fenced sections:\n"
                        "```business_model\n...\n```\n"
                        "```financial\n...\n```\n"
                        "```prd\n...\n```\n"
                        "```tech_spec\n...\n```"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Product name: {state['product_name']}\n"
                        f"Brief:\n{state['brief']}\n\n"
                        f"## Market research\n{state['research_md']}\n\n"
                        f"## Competitors\n{state['competitors_md']}\n\n"
                        f"## Positioning\n{state['positioning_md']}\n\n"
                        f"## Roadmap\n{state['roadmap_md']}\n\n"
                        f"## Marketing\n{state['marketing_md']}"
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or ""
        business_model_md, financial_md, prd_md, tech_spec_md = split_fenced_sections(
            content,
            ("business_model", "financial", "prd", "tech_spec"),
        )
        return {
            "business_model_md": business_model_md,
            "financial_md": financial_md,
            "prd_md": prd_md,
            "tech_spec_md": tech_spec_md,
        }

"""Planning agent: positioning, roadmap, and marketing outline."""

from typing import Any

from openai import AsyncOpenAI

from app.agents.markdown_sections import split_fenced_sections
from app.core.config import Settings, settings


class PlanningAgent:
    """Turn research into positioning, roadmap, and marketing outlines."""

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
            max_completion_tokens=2_800,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Norma AI Planning Agent. Draft three markdown "
                        "sections for a launch strategy pack.\n"
                        "Rules:\n"
                        "- Stay consistent with the research and competitor notes.\n"
                        "- Keep each section actionable and concise.\n"
                        "- Mark unverified claims as **Assumption**.\n"
                        "- Respond with exactly three fenced sections:\n"
                        "```positioning\n...\n```\n"
                        "```roadmap\n...\n```\n"
                        "```marketing\n...\n```"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Product name: {state['product_name']}\n"
                        f"Brief:\n{state['brief']}\n\n"
                        f"## Market research\n{state['research_md']}\n\n"
                        f"## Competitors\n{state['competitors_md']}"
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or ""
        positioning_md, roadmap_md, marketing_md = split_fenced_sections(
            content,
            ("positioning", "roadmap", "marketing"),
        )
        return {
            "positioning_md": positioning_md,
            "roadmap_md": roadmap_md,
            "marketing_md": marketing_md,
        }

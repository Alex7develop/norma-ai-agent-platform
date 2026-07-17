"""Content agent: Cursor prompts, LinkedIn, and Telegram drafts."""

from typing import Any

from openai import AsyncOpenAI

from app.agents.markdown_sections import split_fenced_sections
from app.core.config import Settings, settings


class ContentAgent:
    """Produce builder prompts and channel-ready content drafts."""

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
            temperature=0.4,
            max_completion_tokens=2_800,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Norma AI Content Agent. Draft three markdown "
                        "sections for a launch strategy pack.\n"
                        "Rules:\n"
                        "- Cursor prompts should be concrete implementation prompts "
                        "a developer can paste into Cursor for this initiative.\n"
                        "- LinkedIn: professional launch narrative (1-2 posts).\n"
                        "- Telegram: shorter channel updates (2-3 posts).\n"
                        "- Stay consistent with PRD, positioning, and marketing.\n"
                        "- Mark unverified claims as **Assumption**.\n"
                        "- Respond with exactly three fenced sections:\n"
                        "```cursor_prompts\n...\n```\n"
                        "```linkedin\n...\n```\n"
                        "```telegram\n...\n```"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Product name: {state['product_name']}\n"
                        f"Brief:\n{state['brief']}\n\n"
                        f"## Positioning\n{state['positioning_md']}\n\n"
                        f"## Roadmap\n{state['roadmap_md']}\n\n"
                        f"## Marketing\n{state['marketing_md']}\n\n"
                        f"## Business model\n{state.get('business_model_md', '')}\n\n"
                        f"## PRD\n{state.get('prd_md', '')}\n\n"
                        f"## Tech spec\n{state.get('tech_spec_md', '')}"
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or ""
        cursor_prompts_md, linkedin_md, telegram_md = split_fenced_sections(
            content,
            ("cursor_prompts", "linkedin", "telegram"),
        )
        return {
            "cursor_prompts_md": cursor_prompts_md,
            "linkedin_md": linkedin_md,
            "telegram_md": telegram_md,
        }

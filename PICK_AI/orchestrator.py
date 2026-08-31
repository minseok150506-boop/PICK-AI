from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from question_understanding import (
    analyze_question,
    build_understanding_instruction,
)
from context_resolver import resolve_reference
from tool_planner import plan_route
from question_rewriter import (
    rewrite_for_reasoning,
    build_clarification,
)


@dataclass
class OrchestrationResult:
    analysis: dict[str, Any]
    context: dict[str, Any]
    route: dict[str, Any]
    rewritten_question: str
    understanding_instruction: str
    clarification: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def orchestrate(
    user_message: str,
    history: list[dict] | None = None
) -> OrchestrationResult:
    history = history or []

    analysis = analyze_question(user_message, history)
    context = resolve_reference(user_message, history)
    rewritten = rewrite_for_reasoning(analysis, context)

    # Route using the RESOLVED meaning, not only the short follow-up.
    # Example: "오늘 뉴스" -> "더 알려줘" must stay a news/web request.
    route_analysis = analysis
    if (
        context.resolved
        and rewritten
        and rewritten != analysis.normalized
    ):
        try:
            route_analysis = analyze_question(rewritten, history)
        except Exception:
            route_analysis = analysis

    route = plan_route(route_analysis, context)
    understanding = build_understanding_instruction(analysis)

    if context.resolved:
        understanding += (
            "\n[Resolved conversation context]\n"
            f"{context.referent_summary}\n"
            "The user's current message is a follow-up to this context. "
            "Use the resolved meaning and answer directly. "
            "Do not ask the user what they mean when the recent "
            "conversation already makes it clear.\n"
        )

    clarification = None
    if route.clarify_first:
        clarification = build_clarification(analysis, context)

    return OrchestrationResult(
        analysis=analysis.to_dict(),
        context=context.to_dict(),
        route=route.to_dict(),
        rewritten_question=rewritten,
        understanding_instruction=understanding,
        clarification=clarification,
    )

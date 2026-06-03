"""Agent: formats ranked findings into GitHub inline comments and a summary."""

from app.models import PRReviewState, InlineComment
from app.tools import build_position_map
from app.utils import get_logger, format_inline_body, format_summary_comment

logger = get_logger(__name__)


async def comment_generator_agent(state: PRReviewState) -> PRReviewState:
    ranked = state.get("ranked_findings", [])
    diff = state.get("diff", "")
    meta = state["pr_metadata"]

    # Build diff-position map so inline comments land on valid diff lines
    position_map = build_position_map(diff)

    inline_comments: list[InlineComment] = []

    for finding in ranked:
        pos = position_map.get((finding.file, finding.line))
        comment = InlineComment(
            path=finding.file,
            position=pos,           # None if line isn't in diff
            line=finding.line if pos is None else None,
            body=format_inline_body(finding),
        )
        # Only include inline comment if we have a valid position OR a line number
        if comment.position is not None or comment.line is not None:
            inline_comments.append(comment)

    summary = format_summary_comment(ranked, meta.repo_full_name, meta.pr_number)

    logger.info(
        "comment_generator_done",
        inline=len(inline_comments),
        skipped=len(ranked) - len(inline_comments),
    )

    return {
        "inline_comments": inline_comments,
        "summary_comment": summary,
    }

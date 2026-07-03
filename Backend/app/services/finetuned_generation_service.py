from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent.finetuning.finetuned_agent import FinetunedYamlAgent
from agent.finetuning.model_client import FinetunedModelError
from agent.utils.context_resolver import ContextResolver, build_context_summary
from models.chat_message_model import ChatMessage
from models.chat_session_model import ChatSession
from models.project_model import Project
from models.repository_model import Repository


#Render a single validation error/warning dict as a readable one-liner.
def format_issue(issue: Any) -> str:
    if not isinstance(issue, dict):
        return str(issue)
    message = issue.get("message") or issue.get("detail") or "unknown issue"
    source = issue.get("source")
    if issue.get("line") is not None:
        col = issue.get("col")
        location = f" (line {issue['line']}" + (f", col {col}" if col is not None else "") + ")"
    elif issue.get("path"):
        location = f" (at {issue['path']})"
    else:
        location = ""
    prefix = f"[{source}] " if source else ""
    return f"{prefix}{message}{location}"


#Human-readable validation report shown under an invalid pipeline.
def format_validation_report(report: Optional[dict]) -> str:
    if not report:
        return "**This pipeline did not pass validation** (no report available)."
    lines = ["**This pipeline did not pass validation.**"]
    summary = report.get("summary")
    if summary:
        lines.append(f"Summary: {summary}")
    errors = report.get("errors") or []
    if errors:
        lines.append("\nErrors:")
        lines.extend(f"- {format_issue(e)}" for e in errors)
    warnings = report.get("warnings") or []
    if warnings:
        lines.append("\nWarnings:")
        lines.extend(f"- {format_issue(w)}" for w in warnings)
    return "\n".join(lines)


class FinetunedGenerationService:

    def __init__(self) -> None:
        self._agent = FinetunedYamlAgent()

    async def process(
        self,
        user_id: int,
        message: str,
        session_id: Optional[int],
        project_id: Optional[int],
        pipeline_id: Optional[int],
        platform_override: Optional[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        session = await self._get_or_create_session(user_id, message, session_id, project_id, db)
        session_id = session.id

        if pipeline_id and not session.pipeline_id:
            session.pipeline_id = pipeline_id
            session.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)

        effective_project_id = session.project_id or project_id
        platform, context_summary = await self._resolve_platform_and_context(
            effective_project_id, user_id, platform_override, db
        )

        # run the deterministic generate -> validate -> rectify graph
        try:
            outcome = await self._agent.run(
                description=message,
                platform=platform,
                context_summary=context_summary,
                user_id=user_id,
                db=db,
                project_id=effective_project_id,
            )
        except FinetunedModelError as exc:
            raise HTTPException(status_code=502, detail=f"Finetuned model error: {exc}")

        yaml_text = outcome["yaml"]
        valid = outcome["valid"]

        # The assistant reply is the YAML wrapped in a ```yaml code fence so the frontend renders it in a code block.
        fenced_yaml = f"```yaml\n{yaml_text}\n```"
        if valid:
            assistant_content = fenced_yaml
        else:
            assistant_content = f"{fenced_yaml}\n\n{format_validation_report(outcome['report'])}"

        bot_msg = await self._save_turn(user_id, session_id, message, assistant_content, db)
        bot_timestamp = bot_msg.timestamp
        session_name = session.session_name

        full_history = await self._get_history(user_id, session_id, db)

        return {
            "session_id": session_id,
            "session_name": session_name,
            "platform": platform,
            "valid": valid,
            "yaml": yaml_text,
            "message_content": assistant_content,
            "report": outcome["report"],
            "bot_timestamp": bot_timestamp,
            "full_history": full_history,
        }

    # platform + context
    async def _resolve_platform_and_context(
        self, project_id: Optional[int], user_id: int, platform_override: Optional[str], db: AsyncSession
    ) -> tuple[str, Optional[str]]:
        platform = (platform_override or "").strip().lower() or None
        context_summary: Optional[str] = None

        if project_id:
            # Verify ownership and read the repo platform in one query.
            row = await db.execute(
                select(Repository.platform)
                .join(Project, Project.repo_id == Repository.id)
                .where(Project.id == project_id, Project.user_id == user_id)
            )
            repo_platform = row.scalar_one_or_none()
            if repo_platform is None:
                raise HTTPException(status_code=404, detail="Project not found")
            if not platform:
                platform = (repo_platform or "").strip().lower()

            # Repo context is optional — proceed without it if it isn't available yet.
            try:
                ctx = await ContextResolver(db).get_project_context(project_id)
                context_summary = build_context_summary(ctx.repo_context)
            except Exception:
                context_summary = None

        if platform not in ("github", "gitlab"):
            raise HTTPException(
                status_code=400,
                detail="Target platform could not be determined. Provide 'platform' or link a project with a repository.",
            )
        return platform, context_summary

    # session + message persistence (self-contained)
    async def _get_or_create_session(
        self, user_id: int, message: str, session_id: Optional[int], project_id: Optional[int], db: AsyncSession
    ) -> ChatSession:
        if session_id:
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id, ChatSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found or access denied")
            return session

        session_name = await self._make_session_name(message)
        session = ChatSession(
            user_id=user_id,
            session_name=session_name,
            project_id=project_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def _make_session_name(self, first_message: str) -> str:
        try:
            from agent.chat_session_title import generate_session_title
            title = await generate_session_title(first_message)
        except Exception:
            title = None
        if title:
            return title
        return first_message[:50] + "..." if len(first_message) > 50 else first_message

    async def _save_turn(
        self, user_id: int, session_id: int, user_message: str, bot_response: str, db: AsyncSession
    ) -> ChatMessage:
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
        )
        max_order = len(result.scalars().all())

        db.add(ChatMessage(
            user_id=user_id, chat_session_id=session_id, role="user",
            content=user_message, order_index=max_order,
        ))
        bot_msg = ChatMessage(
            user_id=user_id, chat_session_id=session_id, role="assistant",
            content=bot_response, order_index=max_order + 1,
        )
        db.add(bot_msg)
        await db.execute(
            update(ChatSession).where(ChatSession.id == session_id).values(updated_at=datetime.utcnow())
        )
        await db.commit()
        await db.refresh(bot_msg)
        return bot_msg

    async def _get_history(self, user_id: int, session_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id, ChatMessage.user_id == user_id)
            .order_by(ChatMessage.order_index)
        )
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in result.scalars().all()
        ]

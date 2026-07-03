from __future__ import annotations

import json
from typing import Any, Optional, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from agent.finetuning.model_client import FinetunedModelError
from agent.finetuning.yaml_generator import generate_yaml, rectify_yaml
from services.pipeline_jobs.service import validate_assembled_pipeline


class FinetunedState(TypedDict, total=False):
    description: str
    platform: str
    context_summary: Optional[str]
    yaml: Optional[str]
    report: Optional[dict]
    valid: bool
    attempts: int


#Deterministic generate -> validate -> rectify graph for the fine-tuned model.
class FinetunedYamlAgent:

    def __init__(self, max_attempts: int = 5) -> None:
        self.max_attempts = max_attempts
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(FinetunedState)
        workflow.add_node("generate", self.generate)
        workflow.add_node("validate", self.validate)
        workflow.add_node("rectify", self.rectify)

        workflow.add_edge(START, "generate")
        workflow.add_edge("generate", "validate")
        workflow.add_conditional_edges(
            "validate", self.route_after_validate, {"rectify": "rectify", END: END}
        )
        workflow.add_edge("rectify", "validate")
        return workflow.compile()

#nodes
    async def generate(self, state: FinetunedState, config: RunnableConfig) -> dict:
        yaml_text = await generate_yaml(
            state["description"], state["platform"], state.get("context_summary")
        )
        return {"yaml": yaml_text, "attempts": 1}

    async def validate(self, state: FinetunedState, config: RunnableConfig) -> dict:
        cfg = (config or {}).get("configurable", {})
        report = await validate_assembled_pipeline(
            state.get("yaml") or "",
            state["platform"],
            cfg.get("user_id"),
            cfg.get("db"),
            cfg.get("project_id"),
        )
        return {"report": report, "valid": bool(report.get("valid", False))}

    async def rectify(self, state: FinetunedState, config: RunnableConfig) -> dict:
        update: dict = {"attempts": state.get("attempts", 1) + 1}
        try:
            fixed = await rectify_yaml(
                state["description"],
                state["platform"],
                state.get("context_summary"),
                state.get("yaml") or "",
                json.dumps(state.get("report") or {}, ensure_ascii=False),
            )
        except FinetunedModelError:
            fixed = None  # keep the pre-rectify YAML
        if fixed:
            update["yaml"] = fixed
        return update
#routing
    def route_after_validate(self, state: FinetunedState) -> str:
        if state.get("valid"):
            return END
        if state.get("attempts", 1) < self.max_attempts:
            return "rectify"
        return END

#entry point
    async def run(
        self,
        description: str,
        platform: str,
        context_summary: Optional[str],
        user_id: int,
        db: Any,
        project_id: Optional[int],
    ) -> dict:
        initial: FinetunedState = {
            "description": description,
            "platform": platform,
            "context_summary": context_summary,
            "yaml": None,
            "report": None,
            "valid": False,
            "attempts": 0,
        }
        config = {"configurable": {"user_id": user_id, "db": db, "project_id": project_id}}
        result = await self.graph.ainvoke(initial, config=config)
        return {
            "yaml": result.get("yaml") or "",
            "report": result.get("report"),
            "valid": bool(result.get("valid", False)),
        }

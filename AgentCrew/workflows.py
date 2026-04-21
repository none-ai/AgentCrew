"""
Generic goals and workflow plans for non-domain-specific agent execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Goal:
    title: str
    domain: str = "general"
    outcome: str = ""
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "domain": self.domain,
            "outcome": self.outcome,
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "metadata": dict(self.metadata),
        }


@dataclass
class ToolInvocation:
    name: str
    source: str = "builtin"
    arguments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "arguments": dict(self.arguments),
        }


@dataclass
class WorkflowStep:
    id: str
    title: str
    kind: str = "action"
    capability: str = ""
    tool: Optional[ToolInvocation] = None
    outputs: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "capability": self.capability,
            "tool": self.tool.to_dict() if self.tool else None,
            "outputs": list(self.outputs),
            "notes": self.notes,
        }


@dataclass
class WorkflowPlan:
    goal: Goal
    steps: List[WorkflowStep] = field(default_factory=list)
    context_queries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "context_queries": list(self.context_queries),
        }


def normalize_goal(raw_goal: Any, task_title: str, task_description: str = "", task_type: str = "default", domain: Optional[str] = None) -> Goal:
    if isinstance(raw_goal, Goal):
        return raw_goal

    if isinstance(raw_goal, str) and raw_goal.strip():
        return Goal(
            title=raw_goal.strip(),
            domain=domain or task_type or "general",
            outcome=task_description or raw_goal.strip(),
        )

    if isinstance(raw_goal, dict):
        return Goal(
            title=raw_goal.get("title") or task_title,
            domain=raw_goal.get("domain") or domain or task_type or "general",
            outcome=raw_goal.get("outcome") or task_description,
            success_criteria=list(raw_goal.get("success_criteria", [])),
            constraints=list(raw_goal.get("constraints", [])),
            metadata=dict(raw_goal.get("metadata", {})),
        )

    return Goal(
        title=task_title,
        domain=domain or task_type or "general",
        outcome=task_description,
    )


def normalize_workflow(raw_workflow: Any, task: Any) -> WorkflowPlan:
    metadata = getattr(task, "metadata", {}) or {}
    task_type = metadata.get("task_type", "default")
    goal = normalize_goal(
        metadata.get("goal"),
        getattr(task, "title", ""),
        getattr(task, "description", ""),
        task_type=task_type,
        domain=metadata.get("domain"),
    )

    if isinstance(raw_workflow, WorkflowPlan):
        return raw_workflow

    steps: List[WorkflowStep] = []
    if isinstance(raw_workflow, list):
        for index, item in enumerate(raw_workflow, start=1):
            tool = item.get("tool")
            steps.append(
                WorkflowStep(
                    id=item.get("id", f"step-{index}"),
                    title=item.get("title", f"Step {index}"),
                    kind=item.get("kind", "action"),
                    capability=item.get("capability", task_type),
                    tool=ToolInvocation(**tool) if isinstance(tool, dict) else None,
                    outputs=list(item.get("outputs", [])),
                    notes=item.get("notes", ""),
                )
            )

    if not steps:
        steps = [
            WorkflowStep(
                id="step-1",
                title="Understand goal and constraints",
                kind="analysis",
                capability="planning",
                outputs=["goal brief", "constraints list"],
            ),
            WorkflowStep(
                id="step-2",
                title=f"Execute {task_type or 'general'} work",
                kind="execution",
                capability=task_type or "general",
                tool=ToolInvocation(name="command", source="task_metadata") if metadata.get("command") else None,
                outputs=["primary result"],
            ),
            WorkflowStep(
                id="step-3",
                title="Validate outcome and propose next steps",
                kind="review",
                capability="review",
                outputs=["verification summary", "next-step checklist"],
            ),
        ]

    query_parts = [part for part in [goal.title, goal.outcome, getattr(task, "title", ""), getattr(task, "description", "")] if part]
    return WorkflowPlan(goal=goal, steps=steps, context_queries=query_parts[:3])


def workflow_summary(plan: WorkflowPlan) -> str:
    lines = [f"Goal: {plan.goal.title} [{plan.goal.domain}]"]
    if plan.goal.outcome:
        lines.append(f"Outcome: {plan.goal.outcome}")
    for step in plan.steps:
        lines.append(f"- {step.id}: {step.title} ({step.kind}/{step.capability})")
    return "\n".join(lines)

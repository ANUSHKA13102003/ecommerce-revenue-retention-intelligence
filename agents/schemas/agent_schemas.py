"""
Structured Schemas for the Agentic Analytics System
====================================================
Defines JSON-serializable dataclasses for inter-agent communication,
SQL safety validation, query execution results, and business insights.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SQLValidationResult:
    is_safe: bool
    reason: str
    referenced_tables: list[str] = field(default_factory=list)
    normalized_sql: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChartRecommendation:
    chart_type: str
    x_column: str
    y_column: str
    title: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentQueryResponse:
    question: str
    intent: str
    routed_agent: str
    sql_query: str
    validation: SQLValidationResult
    row_count: int
    data_preview: list[dict[str, Any]]
    source_tables: list[str]
    metric_definitions: list[str]
    factual_summary: str
    business_interpretation: str
    recommended_actions: list[str]
    limitations: list[str]
    chart_recommendation: ChartRecommendation | None = None
    execution_mode: str = "deterministic_local"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


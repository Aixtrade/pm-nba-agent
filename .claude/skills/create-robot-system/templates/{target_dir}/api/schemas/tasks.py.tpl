"""Task API request schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RobotSpec(BaseModel):
    type: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class CreateTaskRequest(BaseModel):
    task_id: str | None = None
    user_id: str = ""
    custom_config: dict[str, Any] = Field(default_factory=dict)
    robots: list[RobotSpec | str] | None = None


class UpdateTaskRequest(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    robots: list[RobotSpec | str] | None = None

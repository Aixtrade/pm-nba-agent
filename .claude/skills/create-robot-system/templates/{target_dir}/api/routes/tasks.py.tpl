"""Task management APIs."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from {package_name}.api.schemas.tasks import CreateTaskRequest, RobotSpec, UpdateTaskRequest
from {package_name}.robots import TaskComposer
from {package_name}.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _redis_from_request(request: Request) -> RedisClient:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise RuntimeError("Redis client missing in app state")
    return redis


def _serialize_robot_specs(robots: list[RobotSpec | str]) -> list[dict[str, Any] | str]:
    serialized: list[dict[str, Any] | str] = []
    for item in robots:
        if isinstance(item, str):
            serialized.append(item)
        else:
            serialized.append(item.model_dump())
    return serialized


async def _load_task_detail(redis: RedisClient, task_id: str) -> dict[str, Any]:
    status_key = Channels.task_status(task_id)
    config_key = Channels.task_config(task_id)
    status_raw = await redis.get(status_key)
    config_raw = await redis.get(config_key)

    status_payload: dict[str, Any] | None = None
    if status_raw:
        try:
            status_payload = TaskStatus.from_json(status_raw).to_dict()
        except Exception:
            status_payload = None

    config_payload: dict[str, Any] | None = None
    robots_payload: list[dict[str, Any] | str] = []
    if config_raw:
        try:
            config = TaskConfig.from_json(config_raw)
            config_payload = config.to_dict()
            robots_raw = config.custom_config.get("robots")
            if isinstance(robots_raw, list):
                robots_payload = robots_raw
        except Exception:
            config_payload = None

    return {
        "task_id": task_id,
        "status": status_payload,
        "config": config_payload,
        "robots": robots_payload,
    }


@router.get("/robots")
async def list_available_robots() -> dict[str, Any]:
    return {"robot_types": TaskComposer.available_robot_types()}


@router.post("")
async def create_task(request: Request, body: CreateTaskRequest) -> dict[str, Any]:
    redis = _redis_from_request(request)
    task_id = body.task_id or f"task-{uuid4().hex[:8]}"

    if await redis.exists(Channels.task_config(task_id)) or await redis.exists(Channels.task_status(task_id)):
        raise HTTPException(status_code=409, detail=f"Task already exists: {task_id}")

    custom_config = dict(body.custom_config)
    if body.robots is not None:
        custom_config["robots"] = _serialize_robot_specs(body.robots)

    config_payload = {
        "task_id": task_id,
        "user_id": body.user_id,
        "custom_config": custom_config,
    }
    message = {
        "action": "create",
        "task_id": task_id,
        "user_id": body.user_id,
        "config": config_payload,
    }
    await redis.publish(Channels.CONTROL, json.dumps(message, ensure_ascii=False))
    return {
        "task_id": task_id,
        "accepted": True,
        "message": "Create command published",
    }


@router.get("")
async def list_tasks(request: Request) -> dict[str, Any]:
    redis = _redis_from_request(request)
    task_ids = sorted(await redis.smembers(Channels.all_tasks()))
    tasks: list[dict[str, Any]] = []
    for task_id in task_ids:
        tasks.append(await _load_task_detail(redis, task_id))
    return {
        "items": tasks,
        "count": len(tasks),
    }


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request) -> dict[str, Any]:
    redis = _redis_from_request(request)
    exists = await redis.exists(Channels.task_config(task_id)) or await redis.exists(Channels.task_status(task_id))
    if not exists:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return await _load_task_detail(redis, task_id)


@router.patch("/{task_id}")
async def update_task(task_id: str, request: Request, body: UpdateTaskRequest) -> dict[str, Any]:
    redis = _redis_from_request(request)
    status_raw = await redis.get(Channels.task_status(task_id))
    if not status_raw:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    try:
        status = TaskStatus.from_json(status_raw)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"Task status broken: {task_id}") from exc

    if status.state not in {TaskState.PENDING, TaskState.RUNNING, TaskState.CANCELLING}:
        raise HTTPException(status_code=409, detail=f"Task is not active: {task_id} ({status.state.value})")

    patch = dict(body.patch)
    if body.robots is not None:
        custom_patch = patch.get("custom_config") or {}
        if not isinstance(custom_patch, dict):
            raise HTTPException(status_code=422, detail="patch.custom_config must be an object")
        custom_patch["robots"] = _serialize_robot_specs(body.robots)
        patch["custom_config"] = custom_patch

    if not patch:
        raise HTTPException(status_code=422, detail="Empty patch")

    message = {
        "action": "update_config",
        "task_id": task_id,
        "patch": patch,
    }
    await redis.publish(Channels.CONTROL, json.dumps(message, ensure_ascii=False))
    return {
        "task_id": task_id,
        "accepted": True,
        "message": "Update command published",
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request, purge: bool = True) -> dict[str, Any]:
    redis = _redis_from_request(request)
    exists = await redis.exists(Channels.task_config(task_id)) or await redis.exists(Channels.task_status(task_id))
    if not exists:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    action = "delete" if purge else "cancel"
    message = {
        "action": action,
        "task_id": task_id,
    }
    await redis.publish(Channels.CONTROL, json.dumps(message, ensure_ascii=False))
    return {
        "task_id": task_id,
        "accepted": True,
        "action": action,
        "message": "Delete command published" if purge else "Cancel command published",
    }

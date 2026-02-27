"""create-robot-system 模板生成器。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
PREFIX_RE = re.compile(r"^[a-zA-Z0-9:_-]+$")


TEMPLATE_ORDER = [
    "{target_dir}/api/main.py.tpl",
    "{target_dir}/api/schemas/tasks.py.tpl",
    "{target_dir}/api/schemas/__init__.py.tpl",
    "{target_dir}/api/routes/tasks.py.tpl",
    "{target_dir}/api/routes/live_stream.py.tpl",
    "{target_dir}/shared/channels.py.tpl",
    "{target_dir}/shared/redis_client.py.tpl",
    "{target_dir}/shared/task_models.py.tpl",
    "{target_dir}/shared/__init__.py.tpl",
    "{target_dir}/robots/base.py.tpl",
    "{target_dir}/robots/{producer_name}.py.tpl",
    "{target_dir}/robots/{consumer_name}.py.tpl",
    "{target_dir}/robots/composer.py.tpl",
    "{target_dir}/robots/__init__.py.tpl",
    "{target_dir}/worker/execution_dedupe.py.tpl",
    "{target_dir}/worker/robot_task.py.tpl",
    "{target_dir}/worker/task_manager.py.tpl",
    "{target_dir}/worker/main.py.tpl",
]


def snake_to_pascal(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_") if part)


def stream_to_enum_member(stream_name: str) -> str:
    """将 stream 名转换为枚举成员名（大写）。"""
    return stream_name.upper()


def parse_streams(raw: str) -> list[str]:
    streams = [part.strip() for part in raw.split(",") if part.strip()]
    if not streams:
        raise ValueError("streams 不能为空")
    invalid = [name for name in streams if not IDENTIFIER_RE.fullmatch(name)]
    if invalid:
        raise ValueError(f"streams 含非法名称: {', '.join(invalid)}")
    return streams


def validate_args(args: argparse.Namespace) -> None:
    for field_name in ("package_name", "producer_name", "consumer_name"):
        value = getattr(args, field_name)
        if not IDENTIFIER_RE.fullmatch(value):
            raise ValueError(f"{field_name} 非法: {value}")

    if not PREFIX_RE.fullmatch(args.prefix):
        raise ValueError(f"prefix 非法: {args.prefix}")


def resolve_target_dir(target_dir: str, workspace_root: Path) -> Path:
    candidate = Path(target_dir)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    candidate = candidate.resolve()

    if candidate == Path("/"):
        raise ValueError("target_dir 不能是根目录")

    if workspace_root not in candidate.parents and candidate != workspace_root:
        raise ValueError(f"target_dir 越界: {candidate}")

    return candidate


def render_text(content: str, replacements: dict[str, str]) -> str:
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def build_stream_blocks(streams: list[str]) -> tuple[str, str]:
    """生成 StreamName 枚举成员和 Channels 常量引用。

    返回：
        enum_members  — 插入 StreamName(StrEnum) 类体的成员行（4 空格缩进）
        const_refs    — 插入 Channels 类体的常量引用行（4 空格缩进）
    """
    enum_lines = [f'    {stream_to_enum_member(name)} = "{name}"' for name in streams]
    ref_lines = [
        f"    STREAM_{stream_to_enum_member(name)} = StreamName.{stream_to_enum_member(name)}"
        for name in streams
    ]
    return "\n".join(enum_lines), "\n".join(ref_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成异步机器人任务系统脚手架")
    parser.add_argument("--package-name", default="my_project")
    parser.add_argument("--prefix", default="my_app")
    parser.add_argument("--target-dir", default="")
    parser.add_argument("--streams", default="data,output,control")
    parser.add_argument("--producer-name", default="sample_producer")
    parser.add_argument("--consumer-name", default="sample_consumer")
    args = parser.parse_args()

    if not args.target_dir:
        args.target_dir = f"{args.package_name}/"

    try:
        validate_args(args)
        streams = parse_streams(args.streams)
    except ValueError as exc:
        print(f"[ERROR] 参数校验失败: {exc}")
        return 2

    workspace_root = Path.cwd().resolve()
    templates_root = (Path(__file__).resolve().parent.parent / "templates").resolve()
    target_dir_abs = resolve_target_dir(args.target_dir, workspace_root)

    producer_class = snake_to_pascal(args.producer_name)
    consumer_class = snake_to_pascal(args.consumer_name)
    primary_stream = streams[0]
    secondary_stream = streams[1] if len(streams) > 1 else streams[0]
    stream_enum_members, stream_const_refs = build_stream_blocks(streams)

    replacements = {
        "package_name": args.package_name,
        "prefix": args.prefix,
        "target_dir": args.target_dir.rstrip("/"),
        "producer_name": args.producer_name,
        "consumer_name": args.consumer_name,
        "ProducerClassName": producer_class,
        "ConsumerClassName": consumer_class,
        "PRIMARY_STREAM": primary_stream,
        "SECONDARY_STREAM": secondary_stream,
        "PRIMARY_STREAM_UPPER": stream_to_enum_member(primary_stream),
        "SECONDARY_STREAM_UPPER": stream_to_enum_member(secondary_stream),
        "STREAM_ENUM_MEMBERS": stream_enum_members,
        "STREAM_CONST_REFS": stream_const_refs,
    }

    generated: list[Path] = []

    for rel_tpl in TEMPLATE_ORDER:
        template_path = templates_root / rel_tpl
        if not template_path.exists():
            print(f"[ERROR] 模板不存在: {template_path}")
            return 3

        rel_without_root = rel_tpl
        if rel_without_root.startswith("{target_dir}/"):
            rel_without_root = rel_without_root[len("{target_dir}/"):]
        rendered_rel = render_text(rel_without_root, replacements)
        target_rel = Path(rendered_rel[:-4])

        target_path = target_dir_abs / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content = template_path.read_text(encoding="utf-8")
        rendered = render_text(content, replacements)
        target_path.write_text(rendered, encoding="utf-8")
        generated.append(target_path)

    for init_dir in (target_dir_abs / "api", target_dir_abs / "api" / "routes"):
        init_dir.mkdir(parents=True, exist_ok=True)
        init_file = init_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""API 包"""\n', encoding="utf-8")
            generated.append(init_file)

    print(f"[OK] 已生成 {len(generated)} 个文件")
    for path in generated:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

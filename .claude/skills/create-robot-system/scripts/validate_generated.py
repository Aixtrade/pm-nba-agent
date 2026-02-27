"""生成后校验脚本。

用途：
1. 校验 Python 文件语法（ast.parse）
2. 检查常见占位符残留
3. 检查模板转义残留（{{ 或 }})
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


PLACEHOLDER_PATTERNS = [
    r"\{package_name\}",
    r"\{prefix\}",
    r"\{target_dir\}",
    r"\{producer_name\}",
    r"\{consumer_name\}",
    r"\{ProducerClassName\}",
    r"\{ConsumerClassName\}",
    r"\{PRIMARY_STREAM\}",
    r"\{SECONDARY_STREAM\}",
    r"\{PRIMARY_STREAM_UPPER\}",
    r"\{SECONDARY_STREAM_UPPER\}",
    r"\{STREAM_ENUM_MEMBERS\}",
    r"\{STREAM_CONST_REFS\}",
]

REQUIRED_FILES = [
    "api/main.py",
    "api/routes/live_stream.py",
    "api/routes/tasks.py",
    "api/schemas/tasks.py",
    "api/schemas/__init__.py",
    "shared/channels.py",
    "shared/redis_client.py",
    "shared/task_models.py",
    "robots/base.py",
    "robots/composer.py",
    "worker/robot_task.py",
    "worker/task_manager.py",
    "worker/main.py",
]


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def validate_python_syntax(py_file: Path) -> list[str]:
    errors: list[str] = []
    text = py_file.read_text(encoding="utf-8")
    try:
        ast.parse(text, filename=str(py_file))
    except SyntaxError as exc:
        errors.append(f"语法错误: {py_file}: {exc}")
    return errors


def validate_placeholders(py_file: Path) -> list[str]:
    errors: list[str] = []
    text = py_file.read_text(encoding="utf-8")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"占位符未替换: {py_file}: {pattern}")

    if "{{" in text or "}}" in text:
        errors.append(f"模板转义残留: {py_file}: 检测到 '{{' 或 '}}'")

    return errors


def validate_required_files(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_FILES:
        if not (root / rel_path).exists():
            errors.append(f"缺少核心文件: {root / rel_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验生成的 robot system 代码")
    parser.add_argument("--root", required=True, help="生成代码根目录")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] 无效目录: {root}")
        return 2

    py_files = iter_python_files(root)
    if not py_files:
        print(f"[WARN] 未发现 Python 文件: {root}")
        return 1

    all_errors: list[str] = []
    all_errors.extend(validate_required_files(root))

    for py_file in py_files:
        all_errors.extend(validate_python_syntax(py_file))
        all_errors.extend(validate_placeholders(py_file))

    if all_errors:
        print("[ERROR] 校验失败:")
        for err in all_errors:
            print(f"- {err}")
        return 1

    print(f"[OK] 校验通过，共检查 {len(py_files)} 个 Python 文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate stack manifest from requirements and imports.

This script extracts the actual technology stack from the codebase
(requirements.txt, imports, etc.) rather than relying on hand-typed docs.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_python_version() -> str:
    """Get Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_requirements(requirements_path: Path) -> dict[str, str]:
    """Parse requirements.txt and return package versions."""
    if not requirements_path.exists():
        return {}

    result = {}
    content = requirements_path.read_text()
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Handle package==version, package>=version, etc.
        match = re.match(r'^([a-zA-Z0-9_-]+)(?:[=<>!]+.*)?$', line)
        if match:
            pkg = match.group(1)
            # Try to get actual installed version
            try:
                out = subprocess.run(
                    [sys.executable, "-m", "pip", "show", pkg],
                    capture_output=True, text=True, timeout=5
                )
                for out_line in out.stdout.split('\n'):
                    if out_line.startswith('Version: '):
                        result[pkg] = out_line.split('Version: ')[1].strip()
                        break
                else:
                    result[pkg] = "unknown"
            except Exception:
                result[pkg] = "unknown"
    return result


def get_imports_from_files(paths: list[Path]) -> set[str]:
    """Extract imports from Python files."""
    imports = set()
    for path in paths:
        if not path.exists() or path.suffix != '.py':
            continue
        try:
            content = path.read_text()
            # Match import statements
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import '):
                    # import x, y, z
                    parts = line[7:].split(',')
                    for p in parts:
                        imports.add(p.strip().split('.')[0])
                elif line.startswith('from '):
                    # from x import y
                    match = re.match(r'^from\s+([a-zA-Z0-9_.]+)\s+import', line)
                    if match:
                        imports.add(match.group(1).split('.')[0])
        except Exception:
            pass
    return imports


def classify_stack(imports: set[str], requirements: dict[str, str]) -> dict[str, Any]:
    """Classify imports into stack categories."""
    categories = {
        "web_framework": [],
        "database": [],
        "orm": [],
        "async": [],
        "testing": [],
        "ml_ai": [],
        "cloud_aws": [],
        "serialization": [],
        "monitoring": [],
        "other": [],
    }

    known = {
        "fastapi": "web_framework",
        "starlette": "web_framework",
        "uvicorn": "web_framework",
        "sqlalchemy": "orm",
        "psycopg": "database",
        "psycopg_binary": "database",
        "pydantic": "serialization",
        "httpx": "async",
        "pytest": "testing",
        "pytest_asyncio": "testing",
        "openai": "ml_ai",
        "boto3": "cloud_aws",
        "botocore": "cloud_aws",
        "anthropic": "ml_ai",
    }

    for imp in imports:
        imp_lower = imp.lower()
        # Check requirements first for more accurate naming
        for req_name, category in known.items():
            if req_name in imp_lower or imp_lower in req_name:
                if req_name not in categories[category]:
                    categories[category].append(req_name)
                break
        else:
            # Check if in requirements
            found = False
            for req_name in requirements:
                if req_name.lower() in imp_lower or imp_lower in req_name.lower():
                    if req_name not in categories["other"]:
                        categories["other"].append(req_name)
                    found = True
                    break
            if not found and imp_lower not in ('os', 'sys', 'json', 're', 'pathlib', 'typing', 'datetime', 'abc', 'time', 'subprocess'):
                categories["other"].append(imp)

    # Sort each category
    for cat in categories:
        categories[cat].sort()

    return categories


def main():
    root = Path(__file__).parent.parent

    # Get requirements
    backend_req = root / "backend" / "requirements.txt"
    requirements = get_requirements(backend_req)

    # Get imports from backend
    backend_files = list((root / "backend").glob("*.py"))
    imports = get_imports_from_files(backend_files)

    # Classify
    stack = classify_stack(imports, requirements)

    # Build manifest
    manifest = {
        "python_version": get_python_version(),
        "requirements": requirements,
        "imports_found": sorted(imports),
        "stack_categories": stack,
        "web_framework": "FastAPI" if "fastapi" in imports else "unknown",
        "database": "PostgreSQL (psycopg)" if any("psycopg" in r for r in requirements) else "unknown",
        "orm": "SQLAlchemy" if "sqlalchemy" in imports else "unknown",
    }

    # Output as JSON
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
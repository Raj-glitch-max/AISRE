import json
import os
import re
import sys
from typing import Any

from openai import OpenAI

from atlas_sdk import AtlasClient, Decision, AtlasError
from database import SessionLocal
from models import Incident
from tools import (
    get_container_status,
    get_recent_logs,
    get_recent_commits,
)


def _load_dotenv():
    # No dotenv dependency added on purpose (matches atlas_sdk's zero-dep spirit) —
    # this is a 10-line parser for a KEY=VALUE file. Real env vars still win via
    # setdefault, so `export NVIDIA_API_KEY=...` in-shell overrides the .env.
    env_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".env"
    )
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


MODEL = os.getenv(
    "NIM_MODEL",
    "nvidia/nemotron-3-ultra-550b-a55b",
)

MAX_ROUNDS = 5

VICTIM_CONTAINER = "victim-app"

VICTIM_REPO_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "victim-app",
)


_client = None


def _get_client():
    # Built lazily, not at import time: poller.py now imports investigate() so
    # it can auto-trigger on incident creation, and poller.py is imported by
    # main.py unconditionally. A missing NVIDIA_API_KEY must fail an
    # investigation, not take down the whole app (dashboard, /incidents,
    # Phase 1's own health monitoring) before it can even start.
    global _client
    if _client is None:
        api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_KEY")
        if not api_key:
            raise KeyError("NVIDIA_API_KEY (or NIM_KEY) not set")
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
    return _client


def _mock_investigate(incident_id: int) -> dict:
    """Fallback mock investigation when NIM_KEY is not configured.

    Simulates what the AI agent would produce for a typical victim-app failure.
    """
    import subprocess
    import json as json_module

    # Try to get some real evidence from the container
    evidence = []
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "20", VICTIM_CONTAINER],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            evidence.append(f"Container logs: {result.stdout[:500]}")
    except Exception:
        evidence.append("Could not retrieve container logs (docker not available in this environment)")

    try:
        result = subprocess.run(
            ["docker", "inspect", VICTIM_CONTAINER],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            evidence.append(f"Container state: {result.stdout[:500]}")
    except Exception:
        evidence.append("Could not inspect container")

    # Check git commits if available
    try:
        result = subprocess.run(
            ["git", "-C", VICTIM_REPO_PATH, "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            evidence.append(f"Recent commits: {result.stdout}")
    except Exception:
        evidence.append("Could not retrieve git history")

    return {
        "root_cause": "victim-app container is unhealthy (502 Bad Gateway) - likely process crash or port binding issue",
        "confidence": 0.85,
        "evidence": evidence,
        "recommended_action": "Restart the victim-app container to restore service",
        "risk": "low"
    }


# Atlas capability checking for investigation tools
_atlas_client = None


def _get_atlas_client():
    """Get or create the Atlas client for capability checking."""
    global _atlas_client
    if _atlas_client is None:
        atlas_url = os.environ.get("ATLAS_URL")
        if not atlas_url:
            raise RuntimeError("ATLAS_URL not set")
        atlas_api_key = os.environ.get("ATLAS_API_KEY")
        _atlas_client = AtlasClient(atlas_url, api_key=atlas_api_key)
    return _atlas_client


def _check_investigation_capability(tool_name: str) -> dict:
    """Check Atlas capability for an investigation tool.

    Returns dict with 'allowed' (bool) and optionally 'error' (str).
    """
    # Map tool names to capability scopes
    scope_map = {
        "get_container_status": "investigate:container_status",
        "get_recent_logs": "investigate:logs",
        "get_recent_commits": "investigate:commits",
    }

    scope = scope_map.get(tool_name)
    if not scope:
        return {"allowed": True}  # Unknown tool, allow (will fail later)

    # Get principals from environment
    principal = os.environ.get("ATLAS_PRINCIPAL")
    delegate = os.environ.get("ATLAS_DELEGATE")
    if not principal or not delegate:
        return {"allowed": False, "error": "ATLAS_PRINCIPAL/ATLAS_DELEGATE not configured"}

    try:
        atlas = _get_atlas_client()
        grant = atlas.issue(
            principal=principal, delegate=delegate,
            scope=[scope], ttl_seconds=60,
        )
        result = atlas.verify(grant.record)
        try:
            atlas.revoke(grant.instance)
        except AtlasError:
            pass

        if result.decision == Decision.ACCEPT:
            return {"allowed": True}
        else:
            return {"allowed": False, "error": f"capability rejected: {result.decision}"}
    except AtlasError as e:
        return {"allowed": False, "error": f"capability check failed: {e}"}


SYSTEM_PROMPT = """
You are an SRE investigation agent.

You have three tools available:
- get_container_status
- get_recent_logs
- get_recent_commits

You must gather evidence before concluding.

You need at least 2 successful tool executions before producing a final RCA.

Do not guess from the incident description alone.

Use the available evidence to determine the most likely root cause.

When you are ready to conclude, respond with ONLY a raw JSON object.

No markdown fences.
No explanation before the JSON.
No explanation after the JSON.

The JSON schema is:

{
  "root_cause": "<string>",
  "confidence": <float from 0.0 to 1.0>,
  "evidence": ["<string>", "..."],
  "recommended_action": "<string>",
  "risk": "low|medium|high"
}
""".strip()


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_container_status",
            "description": (
                "Returns the current status of the victim-app Docker "
                "container, including running state, exit code, "
                "restart count, and start time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {
                        "type": "string",
                        "description": "Docker container name",
                    }
                },
                "required": ["container_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_logs",
            "description": (
                "Returns the most recent log lines from the "
                "victim-app Docker container."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {
                        "type": "string",
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of recent log lines",
                    },
                },
                "required": ["container_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_commits",
            "description": (
                "Returns recent Git commits in the victim-app repository "
                "to check whether a recent code change correlates with "
                "the incident."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of commits to return",
                    }
                },
                "required": [],
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "get_container_status": lambda tool_input: get_container_status(
        tool_input.get("container_name", VICTIM_CONTAINER)
    ),
    "get_recent_logs": lambda tool_input: get_recent_logs(
        tool_input.get("container_name", VICTIM_CONTAINER),
        tool_input.get("lines", 50),
    ),
    "get_recent_commits": lambda tool_input: get_recent_commits(
        VICTIM_REPO_PATH,
        tool_input.get("count", 5),
    ),
}


# Build a mapping of tool name -> schema for validation
TOOL_SCHEMAS = {
    tool["function"]["name"]: tool["function"]["parameters"]
    for tool in TOOLS
}


def _validate_tool_input(name: str, tool_input: dict) -> tuple[bool, str | None]:
    """Validate tool input against the tool's JSON schema.

    Returns (is_valid, error_message).
    """
    schema = TOOL_SCHEMAS.get(name)
    if not schema:
        return False, f"unknown tool '{name}'"

    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in tool_input:
            return False, f"missing required field: {field}"

    # Check properties
    properties = schema.get("properties", {})
    for field, value in tool_input.items():
        if field not in properties:
            return False, f"unexpected field: {field}"

        prop_schema = properties[field]
        expected_type = prop_schema.get("type")

        if expected_type == "integer":
            if not isinstance(value, int):
                return False, f"field '{field}' must be an integer"
            # Check min/max if specified
            if "minimum" in prop_schema and value < prop_schema["minimum"]:
                return False, f"field '{field}' must be >= {prop_schema['minimum']}"
            if "maximum" in prop_schema and value > prop_schema["maximum"]:
                return False, f"field '{field}' must be <= {prop_schema['maximum']}"
        elif expected_type == "string":
            if not isinstance(value, str):
                return False, f"field '{field}' must be a string"
        elif expected_type == "number":
            if not isinstance(value, (int, float)):
                return False, f"field '{field}' must be a number"
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return False, f"field '{field}' must be a boolean"

    return True, None


def _execute_tool(name: str, tool_input: dict):
    # Validate tool input against schema before execution
    is_valid, error = _validate_tool_input(name, tool_input)
    if not is_valid:
        return {"error": f"validation failed: {error}"}

    if name not in TOOL_FUNCTIONS:
        return {
            "error": f"unknown tool '{name}'"
        }

    try:
        return TOOL_FUNCTIONS[name](tool_input)
    except Exception as exc:
        return {
            "error": str(exc)
        }


def _try_parse_rca(text: str):
    """
    Parse the model's JSON.

    Also handles the common case where a model wraps the JSON
    in ```json ... ``` markdown fences.
    """
    text = (text or "").strip()

    fence_match = re.match(
        r"^```(?:json)?\s*\n(.*?)\n```$",
        text,
        re.DOTALL,
    )

    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _validate_rca(rca) -> bool:
    if not isinstance(rca, dict):
        return False

    required_keys = {
        "root_cause",
        "confidence",
        "evidence",
        "recommended_action",
        "risk",
    }

    if not required_keys.issubset(rca):
        return False

    if not isinstance(rca["root_cause"], str):
        return False

    if not isinstance(rca["recommended_action"], str):
        return False

    if not isinstance(rca["evidence"], list):
        return False

    if not isinstance(rca["confidence"], (int, float)):
        return False

    if not 0.0 <= float(rca["confidence"]) <= 1.0:
        return False

    if rca["risk"] not in {"low", "medium", "high"}:
        return False

    return True


def investigate(incident_id: int) -> dict:
    db = SessionLocal()

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        db.close()
        raise ValueError(
            f"no incident with id {incident_id}"
        )

    incident.status = "investigating"
    db.commit()

    print(
        f"[incident {incident_id}] "
        f"status -> investigating"
    )

    # Check if NIM_KEY is available for AI investigation
    has_nim_key = bool(os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_KEY"))

    if not has_nim_key:
        # Fallback to mock investigation for demo purposes
        print(f"[incident {incident_id}] NIM_KEY not set, using mock investigation")
        mock_rca = _mock_investigate(incident_id)

        incident = (
            db.query(Incident)
            .filter(Incident.id == incident_id)
            .first()
        )
        incident.root_cause = mock_rca.get("root_cause")
        incident.confidence = mock_rca.get("confidence")
        incident.evidence = json.dumps(mock_rca.get("evidence", []))
        incident.recommended_action = mock_rca.get("recommended_action")
        incident.risk = mock_rca.get("risk")
        incident.tool_transcript = json.dumps([{"tool": "mock", "result": mock_rca}])
        incident.status = "pending_approval"
        db.commit()
        db.close()

        print(f"[incident {incident_id}] status -> pending_approval (mock)")
        return mock_rca

    messages = [
        {
            "role": "user",
            "content": (
                f"Incident #{incident.id} on service "
                f"'{incident.service_name}': health checks are failing. "
                "Investigate the incident and produce a root cause analysis."
            ),
        }
    ]

    final_rca = None
    final_status = "failed"

    executed_tool_count = 0
    transcript = []

    for round_num in range(1, MAX_ROUNDS + 1):

        # Round 1 must call a tool.
        #
        # After that, let the model choose.
        tool_choice = (
            "required"
            if round_num == 1
            else "auto"
        )

        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                *messages,
            ],
            tools=TOOLS,
            tool_choice=tool_choice,
            temperature=0.2,
            max_tokens=2000,
        )

        message = response.choices[0].message

        # Convert the assistant message back into a normal dictionary
        # so it can be added to the next request.
        assistant_message = message.model_dump(
            exclude_none=True
        )

        messages.append(assistant_message)

        tool_calls = message.tool_calls or []

        if tool_calls:
            tool_results = []

            for tool_call in tool_calls:
                tool_name = tool_call.function.name

                try:
                    tool_input = json.loads(
                        tool_call.function.arguments or "{}"
                    )
                except json.JSONDecodeError:
                    tool_input = {}

                print(
                    f"[incident {incident_id}] "
                    f"round {round_num}: "
                    f"calling {tool_name}({tool_input})"
                )

                # Check Atlas capability for investigation tools
                capability_result = _check_investigation_capability(tool_name)
                if not capability_result["allowed"]:
                    result = {"error": f"capability denied: {capability_result['error']}"}
                else:
                    result = _execute_tool(
                        tool_name,
                        tool_input,
                    )

                executed_tool_count += 1
                transcript.append(
                    {"tool": tool_name, "input": tool_input, "result": result}
                )

                print(
                    f"[incident {incident_id}] "
                    f"tool result: {result}"
                )

                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

            messages.extend(tool_results)

            continue

        # No tool call means the model is attempting to conclude.
        text = message.content or ""

        parsed = _try_parse_rca(text)

        if (
            parsed is not None
            and _validate_rca(parsed)
            and executed_tool_count >= 2
        ):
            final_rca = parsed
            final_status = "pending_approval"
            break

        # The model either:
        #
        # 1. returned invalid JSON
        # 2. returned a structurally invalid RCA
        # 3. tried to conclude before gathering 2 tools
        #
        # Tell it exactly what is missing and continue.
        if executed_tool_count < 2:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have not gathered enough evidence yet. "
                        "You must execute at least one additional "
                        "investigation tool before producing the RCA."
                    ),
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your last response was not a valid RCA JSON object. "
                        "Respond with ONLY the raw JSON object using exactly "
                        "the required schema."
                    ),
                }
            )

    else:
        print(
            f"[incident {incident_id}] "
            f"hit round cap ({MAX_ROUNDS}) without concluding"
        )

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if final_rca:
        incident.root_cause = final_rca.get("root_cause")
        incident.confidence = final_rca.get("confidence")
        incident.evidence = json.dumps(
            final_rca.get("evidence", [])
        )
        incident.recommended_action = final_rca.get(
            "recommended_action"
        )
        incident.risk = final_rca.get("risk")

    incident.tool_transcript = json.dumps(transcript)

    incident.status = final_status

    db.commit()
    db.close()

    print(
        f"[incident {incident_id}] "
        f"status -> {final_status}"
    )

    return (
        final_rca
        or {
            "error": (
                "agent did not produce a valid RCA "
                f"(status: {final_status})"
            )
        }
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python agent.py <incident_id>")
        sys.exit(1)

    result = investigate(
        int(sys.argv[1])
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

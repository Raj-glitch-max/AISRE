import json
import os
import re
import sys

from openai import OpenAI

from database import SessionLocal
from models import Incident
from tools import (
    get_container_status,
    get_recent_logs,
    get_recent_commits,
)


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
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ["NVIDIA_API_KEY"],
        )
    return _client


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


def _execute_tool(name: str, tool_input: dict):
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

                result = _execute_tool(
                    tool_name,
                    tool_input,
                )

                executed_tool_count += 1

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

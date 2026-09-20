"""Investigation tools, in two implementations.

The agent's three tools are the only way it learns anything about the world, and their
output is the ground truth the faithfulness checker scores RCAs against. That makes the
return *shape* load-bearing: `eval/` and `faithfulness_eval.py` both read
`exit_code`/`restart_count` out of `get_container_status`, so both backends must produce
the same keys or the evaluation silently stops working.

PLATFORM=docker (default) shells out to the Docker CLI — local development, and the
platform every result in eval/RESULTS.md was produced on.
PLATFORM=ecs uses the ECS and CloudWatch Logs APIs — Fargate has no Docker socket, so
the docker backend would fail every call there rather than degrade.
"""
import json
import os
import subprocess

PLATFORM = os.getenv("PLATFORM", "docker")

ECS_CLUSTER = os.getenv("ECS_CLUSTER", "")
ECS_SERVICE = os.getenv("ECS_SERVICE", "")
VICTIM_LOG_GROUP = os.getenv("VICTIM_LOG_GROUP", "")


def _boto3():
    import boto3  # imported lazily so the docker path needs no AWS SDK

    return boto3


# --------------------------------------------------------------------------- docker


def _docker_container_status(container_name: str) -> dict:
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {"error": "docker command not found on this machine"}

    if result.returncode != 0:
        return {
            "error": f"container '{container_name}' not found",
            "stderr": result.stderr.strip(),
        }

    try:
        data = json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return {"error": "docker inspect returned unexpected output"}

    state = data["State"]

    return {
        "status": state.get("Status"),
        "running": state.get("Running"),
        "exit_code": state.get("ExitCode"),
        "started_at": state.get("StartedAt"),
        "restart_count": data.get("RestartCount"),
    }


def _docker_recent_logs(container_name: str, lines: int = 50) -> str:
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "error: docker command not found on this machine"

    combined = (result.stdout or "") + (result.stderr or "")
    return combined.strip() or "(no log output)"


# ------------------------------------------------------------------------------ ecs


def _ecs_container_status(container_name: str) -> dict:
    """Same keys as the docker backend.

    A Fargate task has no RestartCount, so it is derived: ECS replaces a stopped task
    rather than restarting it in place, so the count of stopped tasks for this service
    is the closest honest equivalent. exit_code comes from the most recently stopped
    task's container, and is None when nothing has stopped — which the faithfulness
    checker correctly treats as "no evidence for an exit-code claim".
    """
    boto3 = _boto3()
    ecs = boto3.client("ecs")

    try:
        running = ecs.list_tasks(
            cluster=ECS_CLUSTER, serviceName=ECS_SERVICE, desiredStatus="RUNNING"
        )["taskArns"]
        stopped = ecs.list_tasks(
            cluster=ECS_CLUSTER, serviceName=ECS_SERVICE, desiredStatus="STOPPED"
        )["taskArns"]
    except Exception as exc:
        return {"error": f"ecs list_tasks failed: {exc}"}

    exit_code = None
    started_at = None

    if running:
        described = ecs.describe_tasks(cluster=ECS_CLUSTER, tasks=running[:1])["tasks"]
        if described:
            started_at = str(described[0].get("startedAt", "")) or None

    if stopped:
        described = ecs.describe_tasks(cluster=ECS_CLUSTER, tasks=stopped[:1])["tasks"]
        if described:
            containers = described[0].get("containers", [])
            if containers:
                exit_code = containers[0].get("exitCode")

    return {
        "status": "running" if running else "stopped",
        "running": bool(running),
        "exit_code": exit_code,
        "started_at": started_at,
        "restart_count": len(stopped),
    }


def _ecs_recent_logs(container_name: str, lines: int = 50) -> str:
    boto3 = _boto3()
    logs = boto3.client("logs")

    if not VICTIM_LOG_GROUP:
        return "error: VICTIM_LOG_GROUP is not configured"

    try:
        streams = logs.describe_log_streams(
            logGroupName=VICTIM_LOG_GROUP,
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )["logStreams"]
    except Exception as exc:
        return f"error: could not list log streams: {exc}"

    if not streams:
        return "(no log output)"

    try:
        events = logs.get_log_events(
            logGroupName=VICTIM_LOG_GROUP,
            logStreamName=streams[0]["logStreamName"],
            limit=lines,
            startFromHead=False,
        )["events"]
    except Exception as exc:
        return f"error: could not read log events: {exc}"

    return "\n".join(e["message"].rstrip() for e in events) or "(no log output)"


# -------------------------------------------------------------------------- dispatch


def get_container_status(container_name: str) -> dict:
    if PLATFORM == "ecs":
        return _ecs_container_status(container_name)
    return _docker_container_status(container_name)


def get_recent_logs(container_name: str, lines: int = 50) -> str:
    if PLATFORM == "ecs":
        return _ecs_recent_logs(container_name, lines)
    return _docker_recent_logs(container_name, lines)


def get_recent_commits(repo_path: str, count: int = 5) -> list:
    """Platform-independent: the repo travels with the image."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--pretty=format:%h|%an|%ad|%s", "--date=iso"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
    except FileNotFoundError:
        return [{"error": "git command not found on this machine"}]

    if result.returncode != 0:
        return [{"error": result.stderr.strip()}]

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                }
            )
    return commits


if __name__ == "__main__":
    print(f"=== platform: {PLATFORM} ===")
    print("=== get_container_status ===")
    print(get_container_status(os.getenv("VICTIM_CONTAINER", "victim-app")))

    print("=== get_recent_logs ===")
    print(get_recent_logs(os.getenv("VICTIM_CONTAINER", "victim-app"), lines=10))

    print("=== get_recent_commits ===")
    repo = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "victim-app"
    )
    print(get_recent_commits(repo, count=5))

import json
import subprocess


def get_container_status(container_name: str) -> dict:
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {
            "error": "docker command not found on this machine"
        }

    if result.returncode != 0:
        return {
            "error": f"container '{container_name}' not found",
            "stderr": result.stderr.strip(),
        }

    try:
        data = json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return {
            "error": "docker inspect returned unexpected output"
        }

    state = data["State"]

    return {
        "status": state.get("Status"),
        "running": state.get("Running"),
        "exit_code": state.get("ExitCode"),
        "started_at": state.get("StartedAt"),
        "restart_count": data.get("RestartCount"),
    }


def get_recent_logs(container_name: str, lines: int = 50) -> str:
    try:
        result = subprocess.run(
            [
                "docker",
                "logs",
                "--tail",
                str(lines),
                container_name,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "error: docker command not found on this machine"

    combined = (result.stdout or "") + (result.stderr or "")

    return combined.strip() or "(no log output)"


def get_recent_commits(repo_path: str, count: int = 5) -> list:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{count}",
                "--pretty=format:%h|%an|%ad|%s",
                "--date=iso",
            ],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
    except FileNotFoundError:
        return [
            {
                "error": "git command not found on this machine"
            }
        ]

    if result.returncode != 0:
        return [
            {
                "error": result.stderr.strip()
            }
        ]

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
    import os

    print("=== get_container_status ===")
    print(get_container_status("victim-app"))

    print("=== get_recent_logs ===")
    print(get_recent_logs("victim-app", lines=10))

    print("=== get_recent_commits ===")

    repo = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "victim-app",
    )

    print(get_recent_commits(repo, count=5))

"""Parse logs/*.log JSON lines and print aggregate metrics."""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_log_file(path: str):
    metrics = []
    tools = defaultdict(int)
    errors = defaultdict(int)

    with open(path, encoding="utf-8") as f:
        for line in f:
            if "{" not in line:
                continue
            try:
                start = line.index("{")
                payload = json.loads(line[start:])
            except (json.JSONDecodeError, ValueError):
                continue

            event = payload.get("event")
            data = payload.get("data", {})
            if event == "LLM_METRIC":
                metrics.append(data)
            elif event == "TOOL_CALL":
                tools[data.get("tool", "?")] += 1
            elif event in ("PARSE_ERROR", "TOOL_ERROR", "PARSE_WARNING"):
                errors[event] += 1

    if not metrics:
        print(f"No LLM_METRIC in {path}")
        return

    latencies = [m.get("latency_ms", 0) for m in metrics]
    tokens = [m.get("total_tokens", 0) for m in metrics]
    costs = [m.get("cost_estimate", 0) for m in metrics]

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"LLM calls: {len(metrics)}")
    print(f"Avg latency (ms): {sum(latencies) / len(latencies):.0f}")
    print(f"Avg tokens: {sum(tokens) / len(tokens):.0f}")
    print(f"Total cost estimate: ${sum(costs):.4f}")
    if tools:
        print("Tool calls:", dict(tools))
    if errors:
        print("Errors:", dict(errors))


def main():
    log_dir = os.path.join(ROOT, "logs")
    if not os.path.isdir(log_dir):
        print("No logs/ directory yet. Run chatbot or agent first.")
        sys.exit(1)
    files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])
    if not files:
        print("No .log files found.")
        sys.exit(1)
    for name in files:
        parse_log_file(os.path.join(log_dir, name))


if __name__ == "__main__":
    main()

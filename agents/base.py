import json
import anthropic
from rich.console import Console

console = Console()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


def run_agent(name: str, system: str, user_msg: str, tools: list, handlers: dict) -> str:
    """Run a Claude agent with tool calling until end_turn."""
    messages = [{"role": "user", "content": user_msg}]

    while True:
        resp = client.messages.create(
            model=MODEL, max_tokens=1500,
            system=system, tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                console.print(f"    [dim]→ [{name}] {block.name}({block.input})[/dim]")
                handler = handlers.get(block.name)
                result = handler(**block.input) if handler else {"error": "Unknown tool"}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})


def extract_json(text: str):
    """Safely parse JSON from Claude output, stripping markdown fences."""
    import re
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

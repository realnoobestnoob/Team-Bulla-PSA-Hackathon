"""
Base agent runner for Google AI Studio (google-genai SDK).
Changes from v1:
  - set_model() / get_last_token_usage() for dashboard control
  - on_step callback for real-time tool-call streaming to Streamlit
  - Array schema support in _build_tools for batch tools
  - Token accumulation across all turns in the while-loop
"""
import json, os, re
from google import genai
from google.genai import types
from rich.console import Console

console = Console()

MODEL   = "gemini-3.7-flash"          # default; overridden by set_model()
_client = None
_last_token_usage: dict = {}


# ── Public helpers ────────────────────────────────────────────────────────────

def set_model(model_name: str) -> None:
    """Switch the active model (called from dashboard sidebar)."""
    global MODEL
    MODEL = model_name


def get_last_token_usage() -> dict:
    """Return prompt/completion/total token counts from the last run_agent call."""
    return _last_token_usage.copy()


# ── Internal ──────────────────────────────────────────────────────────────────

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _client


def _prop_schema(prop: dict) -> types.Schema:
    """Convert a JSON-schema property dict to a google.genai Schema."""
    t    = prop.get("type", "string").lower()
    desc = prop.get("description", "")
    if t == "array":
        item_type = prop.get("items", {}).get("type", "string").upper()
        return types.Schema(type="ARRAY", items=types.Schema(type=item_type), description=desc)
    if t in ("integer", "int"):
        return types.Schema(type="INTEGER", description=desc)
    if t in ("number", "float"):
        return types.Schema(type="NUMBER", description=desc)
    if t == "boolean":
        return types.Schema(type="BOOLEAN", description=desc)
    return types.Schema(type="STRING", description=desc)


def _build_tools(tool_defs: list) -> list:
    declarations = []
    for t in tool_defs:
        schema = t["input_schema"]
        props  = {k: _prop_schema(v) for k, v in schema.get("properties", {}).items()}
        declarations.append(types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=types.Schema(
                type="OBJECT",
                properties=props,
                required=schema.get("required", []),
            ),
        ))
    return [types.Tool(function_declarations=declarations)]


def run_agent(
    name:      str,
    system:    str,
    user_msg:  str,
    tool_defs: list,
    handlers:  dict,
    on_step=None,          # callable(str) → streamed to UI
) -> str:
    """
    Run a Gemini agent until no further function calls.
    Accumulates token usage in _last_token_usage.
    """
    global _last_token_usage

    chat = _get_client().chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system,
            tools=_build_tools(tool_defs),
        ),
    )
    response = chat.send_message(user_msg)

    prompt_tokens = 0
    completion_tokens = 0

    while True:
        # Accumulate tokens from each API round-trip
        um = getattr(response, "usage_metadata", None)
        if um:
            prompt_tokens     = getattr(um, "prompt_token_count",     prompt_tokens) or prompt_tokens
            completion_tokens += getattr(um, "candidates_token_count", 0) or 0

        parts    = response.candidates[0].content.parts
        fn_calls = [p for p in parts if p.function_call]

        if not fn_calls:
            text = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
            _last_token_usage = {
                "prompt_tokens":     prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens":      prompt_tokens + completion_tokens,
            }
            return text

        fn_responses = []
        for p in fn_calls:
            fc   = p.function_call
            args = dict(fc.args)
            msg  = f"🔧 {fc.name}({args})"
            console.print(f"    [dim]→ [{name}] {fc.name}({args})[/dim]")
            if on_step:
                on_step(msg)

            handler = handlers.get(fc.name)
            result  = handler(**args) if handler else {"error": f"Unknown tool: {fc.name}"}
            fn_responses.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": json.dumps(result)},
                )
            )
        response = chat.send_message(fn_responses)


def extract_json(text: str):
    """Strip markdown fences and parse first JSON object/array found."""
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        return json.loads(m.group()) if m else []

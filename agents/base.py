import json, os, re
from google import genai
from google.genai import types
from rich.console import Console

console = Console()
MODEL = "gemini-3.6-flash"
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _client


def _build_tools(tool_defs: list) -> list:
    """Convert tool_defs to google.genai FunctionDeclaration objects."""
    declarations = []
    for t in tool_defs:
        schema = t["input_schema"]
        props  = {
            k: types.Schema(
                type=v.get("type", "STRING").upper(),
                description=v.get("description", ""),
            )
            for k, v in schema.get("properties", {}).items()
        }
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


def run_agent(name: str, system: str, user_msg: str, tool_defs: list, handlers: dict) -> str:
    """Run a Gemini agent with tool calling until no further function calls."""
    chat = _get_client().chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system,
            tools=_build_tools(tool_defs),
        ),
    )
    response = chat.send_message(user_msg)

    while True:
        parts    = response.candidates[0].content.parts
        fn_calls = [p for p in parts if p.function_call]

        if not fn_calls:
            return "".join(p.text for p in parts if hasattr(p, "text") and p.text)

        fn_responses = []
        for p in fn_calls:
            fc   = p.function_call
            args = dict(fc.args)
            console.print(f"    [dim]→ [{name}] {fc.name}({args})[/dim]")
            handler = handlers.get(fc.name)
            result  = handler(**args) if handler else {"error": "Unknown tool"}
            fn_responses.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": json.dumps(result)},
                )
            )
        response = chat.send_message(fn_responses)


def extract_json(text: str):
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        return json.loads(m.group()) if m else []

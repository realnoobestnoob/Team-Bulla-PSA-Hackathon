import json
import os
import google.generativeai as genai
from rich.console import Console

console = Console()
MODEL = "gemini-2.0-flash"

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def _convert_tools(anthropic_tools: list) -> list:
    """Convert Anthropic tool schema format to Google FunctionDeclaration format."""
    declarations = [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }
        for t in anthropic_tools
    ]
    return [{"function_declarations": declarations}]


def run_agent(name: str, system: str, user_msg: str, tools: list, handlers: dict) -> str:
    """Run a Gemini agent with tool calling until no more function calls."""
    google_tools = _convert_tools(tools)
    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=system,
        tools=google_tools,
    )

    chat = model.start_chat()
    response = chat.send_message(user_msg)

    while True:
        fn_calls = [
            p for p in response.parts
            if hasattr(p, "function_call") and p.function_call.name
        ]

        if not fn_calls:
            return response.text

        fn_responses = []
        for part in fn_calls:
            fc = part.function_call
            args = dict(fc.args)
            console.print(f"    [dim]→ [{name}] {fc.name}({args})[/dim]")
            handler = handlers.get(fc.name)
            result = handler(**args) if handler else {"error": "Unknown tool"}
            fn_responses.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name,
                        response={"result": json.dumps(result)},
                    )
                )
            )

        response = chat.send_message(fn_responses)


def extract_json(text: str):
    """Safely parse JSON from model output, stripping markdown fences."""
    import re
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

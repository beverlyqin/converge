import json

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.tools.flight_tools import search_meetup_options
from backend.app.tools.lounge_tools import (
    find_lounges,
    get_lounge_policy,
)


tools = [
    search_meetup_options,
    find_lounges,
    get_lounge_policy,
]

tools_by_name = {
    tool.name: tool
    for tool in tools
}


model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
)

model_with_tools = model.bind_tools(tools)


SYSTEM_PROMPT = (
    "You are a flight meetup and airport lounge assistant. "
    "Use only information returned by the available tools. "
    "Do not invent flight options, lounge locations, or access rules. "
    "Preserve policy wording and strength exactly. "
    "If evidence says 'may', do not change it to 'must'. "
    "Do not omit restrictive qualifiers from tool evidence. "
    "If access depends on a condition that the user has not provided, "
    "describe the lounge as conditionally accessible rather than saying "
    "the user definitely has access. "
    "If information is unavailable, say so."
)


def run_meetup_agent(question: str) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]

    while True:
        response = model_with_tools.invoke(messages)

        messages.append(response)

        if not response.tool_calls:
            return response.text

        for tool_call in response.tool_calls:
            tool = tools_by_name[tool_call["name"]]

            result = tool.invoke(
                tool_call["args"]
            )

            messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call["id"],
                )
            )
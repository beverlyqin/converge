from langchain_core.messages import AIMessage

from backend.app.agent.meetup_agent import run_tool_loop


class FakeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.message_counts = []

    def invoke(self, messages):
        self.message_counts.append(len(messages))
        return next(self.responses)


class FakeTool:
    def __init__(self, name, result, calls):
        self.name = name
        self.result = result
        self.calls = calls

    def invoke(self, args):
        self.calls.append((self.name, args))
        return self.result


def tool_call(name, args, call_id):
    return {
        "name": name,
        "args": args,
        "id": call_id,
        "type": "tool_call",
    }


def test_agent_orchestrates_flight_lounge_and_policy_tools_in_sequence():
    calls = []

    model = FakeModel([
        AIMessage(
            content="",
            tool_calls=[
                tool_call(
                    "search_meetup_options",
                    {
                        "origin_a": "JFK",
                        "origin_b": "SEA",
                    },
                    "flight-call",
                )
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                tool_call(
                    "find_lounges",
                    {
                        "card": "Amex Platinum",
                        "airport": "JFK",
                    },
                    "lounge-call",
                )
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                tool_call(
                    "get_lounge_policy",
                    {
                        "card": "Amex Platinum",
                        "lounge_network": "Centurion Lounge",
                    },
                    "policy-call",
                )
            ],
        ),
        AIMessage(
            content="Austin is the best meetup option, with grounded JFK lounge details."
        ),
    ])

    tool_map = {
        "search_meetup_options": FakeTool(
            "search_meetup_options",
            {
                "results": [
                    {
                        "destination": "AUS",
                        "metrics": {
                            "arrival_gap_minutes": 95.0,
                        },
                    }
                ]
            },
            calls,
        ),
        "find_lounges": FakeTool(
            "find_lounges",
            {
                "matched_lounge_networks": [
                    "Centurion Lounge",
                ],
                "lounges": [
                    {
                        "name": "JFK Centurion Lounge",
                    }
                ],
            },
            calls,
        ),
        "get_lounge_policy": FakeTool(
            "get_lounge_policy",
            {
                "card": "Amex Platinum",
                "lounge_network": "Centurion Lounge",
                "evidence": [
                    {
                        "content": "Access requires an eligible same-day boarding pass.",
                    }
                ],
            },
            calls,
        ),
    }

    answer = run_tool_loop(
        question=(
            "Find a meetup for JFK and SEA and tell me "
            "what JFK lounges I can use with Amex Platinum."
        ),
        model_with_tools=model,
        tool_map=tool_map,
    )

    assert answer == (
        "Austin is the best meetup option, "
        "with grounded JFK lounge details."
    )

    assert [name for name, _ in calls] == [
        "search_meetup_options",
        "find_lounges",
        "get_lounge_policy",
    ]

    assert calls[0][1]["origin_a"] == "JFK"
    assert calls[0][1]["origin_b"] == "SEA"
    assert calls[1][1] == {
        "card": "Amex Platinum",
        "airport": "JFK",
    }
    assert calls[2][1] == {
        "card": "Amex Platinum",
        "lounge_network": "Centurion Lounge",
    }

    assert model.message_counts == [2, 4, 6, 8]

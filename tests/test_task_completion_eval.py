from scripts.evaluate_task_completion import (
    TracedTool,
    load_task_completion_cases,
)

class FakeTool:
    name = "fake_tool"

    def __init__(self):
        self.received_args = None

    def invoke(self, args):
        self.received_args = args

        return {
            "result": "success",
        }


def test_traced_tool_preserves_name_and_invokes_tool():
    fake_tool = FakeTool()

    traced_tool = TracedTool(fake_tool)

    result = traced_tool.invoke(
        {
            "airport": "JFK",
        }
    )

    assert traced_tool.name == "fake_tool"

    assert fake_tool.received_args == {
        "airport": "JFK",
    }

    assert result == {
        "result": "success",
    }

def test_load_task_completion_cases():
    cases = load_task_completion_cases()

    assert len(cases) == 4

    assert cases[0]["id"] == "flight_search"

    assert {
        case["category"]
        for case in cases
    } == {
        "flight_search",
        "lounge_lookup",
        "mixed",
        "lounge_policy",
    }
from langchain_core.messages import AIMessage

from scripts.evaluate_agent_live import arguments_match, flight_arguments_match, normalize_datetime, travelers_match
from backend.app.agent.meetup_agent import run_tool_loop
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams

class FakeModel:
    def __init__(self, responses):
        self.responses = responses
        self.index = 0

    def invoke(self, messages):
        response = self.responses[self.index]
        self.index += 1
        return response


class FakeTool:
    def __init__(self, result):
        self.result = result

    def invoke(self, args):
        return self.result
    
def trace_to_tool_calls(trace):
    return [
        ToolCall(
            name=call["name"],
            input_parameters=call["args"],
        )
        for call in trace
    ]

def test_correct_flight_search_tool():
    test_case = LLMTestCase(
        input="Find a meetup destination for JFK and SEA.",
        actual_output="I found a meetup option.",
        tools_called=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                },
            )
        ],
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                },
            )
        ],
    )

    metric = ToolCorrectnessMetric()

    metric.measure(test_case)

    print("score:", metric.score)
    print("reason:", metric.reason)

    assert metric.score == 1.0


def test_wrong_tool_is_detected():
    test_case = LLMTestCase(
        input="Find a meetup destination for JFK and SEA.",
        actual_output="Here are some lounges.",
        tools_called=[
            ToolCall(
                name="find_lounges",
            )
        ],
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
            )
        ],
    )

    metric = ToolCorrectnessMetric()

    metric.measure(test_case)

    print("score:", metric.score)
    print("reason:", metric.reason)

    assert metric.score == 0.0

def test_wrong_flight_arguments_are_detected():
    test_case = LLMTestCase(
        input="Find a meetup destination for JFK and SEA.",
        actual_output="I found a meetup option.",
        tools_called=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "LAX",
                },
            )
        ],
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                },
            )
        ],
    )

    metric = ToolCorrectnessMetric(
        evaluation_params=[
            ToolCallParams.INPUT_PARAMETERS
        ],
        should_exact_match=True,
    )

    metric.measure(test_case)

    print("argument score:", metric.score)
    print("argument reason:", metric.reason)

    assert metric.score == 0.0

def test_arrival_gap_constraint_is_preserved():
    test_case = LLMTestCase(
        input=(
            "Find a meetup destination for JFK and SEA "
            "with no more than a 2 hour arrival gap."
        ),
        actual_output="I found a meetup option.",
        tools_called=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                    "max_arrival_gap_minutes": 120,
                },
            )
        ],
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                    "max_arrival_gap_minutes": 120,
                },
            )
        ],
    )

    metric = ToolCorrectnessMetric(
        evaluation_params=[
            ToolCallParams.INPUT_PARAMETERS
        ],
        should_exact_match=True,
    )

    metric.measure(test_case)

    print("constraint score:", metric.score)
    print("constraint reason:", metric.reason)

    assert metric.score == 1.0

def test_multiple_flight_constraints_are_preserved():
    test_case = LLMTestCase(
        input=(
            "Find a meetup destination for JFK and SEA "
            "with at most one stop and no more than a 2 hour arrival gap."
        ),
        actual_output="I found a meetup option.",
        tools_called=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                    "max_stops": 1,
                    "max_arrival_gap_minutes": 120,
                },
            )
        ],
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                    "max_stops": 1,
                    "max_arrival_gap_minutes": 120,
                },
            )
        ],
    )

    metric = ToolCorrectnessMetric(
        evaluation_params=[
            ToolCallParams.INPUT_PARAMETERS
        ],
        should_exact_match=True,
    )

    metric.measure(test_case)

    print("multi-constraint score:", metric.score)
    print("multi-constraint reason:", metric.reason)

    assert metric.score == 1.0

def test_trace_converts_to_deepeval_tool_calls():
    trace = [
        {
            "name": "search_meetup_options",
            "args": {
                "origin_a": "JFK",
                "origin_b": "SEA",
                "max_stops": 1,
                "max_arrival_gap_minutes": 120,
            },
        }
    ]

    tool_calls = trace_to_tool_calls(trace)

    assert len(tool_calls) == 1

    assert tool_calls[0].name == "search_meetup_options"

    assert tool_calls[0].input_parameters == {
        "origin_a": "JFK",
        "origin_b": "SEA",
        "max_stops": 1,
        "max_arrival_gap_minutes": 120,
    }

def test_agent_trace_is_scored_by_deepeval():
    model = FakeModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_meetup_options",
                        "args": {
                            "origin_a": "JFK",
                            "origin_b": "SEA",
                            "max_stops": 1,
                            "max_arrival_gap_minutes": 120,
                        },
                        "id": "flight-call",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="Austin is a meetup option."
            ),
        ]
    )

    tool_map = {
        "search_meetup_options": FakeTool(
            {
                "results": [
                    {
                        "destination": "AUS",
                    }
                ]
            }
        )
    }

    answer, trace = run_tool_loop(
        question=(
            "Find a meetup destination for JFK and SEA "
            "with at most one stop and no more than "
            "a 2 hour arrival gap."
        ),
        model_with_tools=model,
        tool_map=tool_map,
        return_trace=True,
    )

    actual_tools = trace_to_tool_calls(trace)

    test_case = LLMTestCase(
        input=(
            "Find a meetup destination for JFK and SEA "
            "with at most one stop and no more than "
            "a 2 hour arrival gap."
        ),
        actual_output=answer,
        tools_called=actual_tools,
        expected_tools=[
            ToolCall(
                name="search_meetup_options",
                input_parameters={
                    "origin_a": "JFK",
                    "origin_b": "SEA",
                    "max_stops": 1,
                    "max_arrival_gap_minutes": 120,
                },
            )
        ],
    )

    metric = ToolCorrectnessMetric(
        evaluation_params=[
            ToolCallParams.INPUT_PARAMETERS
        ],
        should_exact_match=True,
    )

    metric.measure(test_case)

    print("end-to-end tool score:", metric.score)
    print("end-to-end reason:", metric.reason)

    assert metric.score == 1.0

def test_normalize_datetime_ignores_seconds():
    first = normalize_datetime(
        "2026-11-13T23:59:00"
    )

    second = normalize_datetime(
        "2026-11-13T23:59:59"
    )

    assert first == second

def test_travelers_match_when_a_and_b_are_swapped():
    expected = {
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:59",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
    }

    actual = {
        "origin_a": "SEA",
        "depart_after_a": "2026-11-13T14:00:00",
        "depart_before_a": "2026-11-13T20:00:00",
        "origin_b": "JFK",
        "depart_after_b": "2026-11-13T17:00:00",
        "depart_before_b": "2026-11-13T23:59:00",
    }

    assert travelers_match(actual, expected)

def test_travelers_do_not_match_with_wrong_time_windows():
    expected = {
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:59",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
    }

    actual = {
        "origin_a": "SEA",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:00",
        "origin_b": "JFK",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
    }

    assert not travelers_match(actual, expected)

def test_flight_arguments_match_semantically():
    expected = {
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:59",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
        "max_stops": 0,
        "max_arrival_gap_minutes": 60,
    }

    actual = {
        "origin_a": "SEA",
        "depart_after_a": "2026-11-13T14:00:00",
        "depart_before_a": "2026-11-13T20:00:00",
        "origin_b": "JFK",
        "depart_after_b": "2026-11-13T17:00:00",
        "depart_before_b": "2026-11-13T23:59:00",
        "max_stops": 0,
        "max_arrival_gap_minutes": 60,
    }

    assert flight_arguments_match(
        actual,
        expected,
    )

def test_flight_arguments_detect_wrong_constraint():
    expected = {
        "origin_a": "JFK",
        "depart_after_a": "2026-11-13T17:00:00",
        "depart_before_a": "2026-11-13T23:59:59",
        "origin_b": "SEA",
        "depart_after_b": "2026-11-13T14:00:00",
        "depart_before_b": "2026-11-13T20:00:00",
        "max_stops": 0,
        "max_arrival_gap_minutes": 60,
    }

    actual = {
        "origin_a": "SEA",
        "depart_after_a": "2026-11-13T14:00:00",
        "depart_before_a": "2026-11-13T20:00:00",
        "origin_b": "JFK",
        "depart_after_b": "2026-11-13T17:00:00",
        "depart_before_b": "2026-11-13T23:59:00",
        "max_stops": 1,
        "max_arrival_gap_minutes": 60,
    }

    assert not flight_arguments_match(
        actual,
        expected,
    )

def test_arguments_match_mixed_tools():
    expected_tools = [
        {
            "name": "search_meetup_options",
            "args": {
                "origin_a": "JFK",
                "depart_after_a": "2026-11-13T17:00:00",
                "depart_before_a": "2026-11-13T23:59:59",
                "origin_b": "SEA",
                "depart_after_b": "2026-11-13T14:00:00",
                "depart_before_b": "2026-11-13T20:00:00",
                "max_stops": 1,
                "max_arrival_gap_minutes": 120,
            },
        },
        {
            "name": "find_lounges",
            "args": {
                "card": "Amex Platinum",
                "airport": "JFK",
            },
        },
    ]

    actual_trace = [
        {
            "name": "find_lounges",
            "args": {
                "card": "Amex Platinum",
                "airport": "JFK",
            },
        },
        {
            "name": "search_meetup_options",
            "args": {
                "origin_a": "SEA",
                "depart_after_a": "2026-11-13T14:00:00",
                "depart_before_a": "2026-11-13T20:00:00",
                "origin_b": "JFK",
                "depart_after_b": "2026-11-13T17:00:00",
                "depart_before_b": "2026-11-13T23:59:00",
                "max_stops": 1,
                "max_arrival_gap_minutes": 120,
            },
        },
    ]

    assert arguments_match(
        actual_trace,
        expected_tools,
    )
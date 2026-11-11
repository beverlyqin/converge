import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from backend.app.agent.meetup_agent import (
    get_model_with_tools,
    run_tool_loop,
    tools_by_name,
)
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import (
    LLMTestCase,
    ToolCall,
)

load_dotenv()

def normalize_datetime(value: str) -> str:
    dt = datetime.fromisoformat(value)

    return dt.strftime("%Y-%m-%dT%H:%M")

def trace_to_tool_calls(trace):
    return [
        ToolCall(
            name=call["name"],
            input_parameters=call["args"],
        )
        for call in trace
    ]

def expected_tools_to_tool_calls(expected_tools):
    return [
        ToolCall(
            name=tool["name"],
            input_parameters=tool["args"],
        )
        for tool in expected_tools
    ]

def load_eval_cases():
    project_root = Path(__file__).resolve().parents[1]

    cases_path = (
        project_root
        / "data"
        / "agent_eval_cases.json"
    )

    return json.loads(
        cases_path.read_text(encoding="utf-8")
    )

def get_travelers(args):
    traveler_a = {
        "origin": args["origin_a"],
        "depart_after": normalize_datetime(
            args["depart_after_a"]
        ),
        "depart_before": normalize_datetime(
            args["depart_before_a"]
        ),
    }

    traveler_b = {
        "origin": args["origin_b"],
        "depart_after": normalize_datetime(
            args["depart_after_b"]
        ),
        "depart_before": normalize_datetime(
            args["depart_before_b"]
        ),
    }

    return [traveler_a, traveler_b]

def travelers_match(actual_args, expected_args):
    actual = get_travelers(actual_args)
    expected = get_travelers(expected_args)

    actual = sorted(
        actual,
        key=lambda traveler: traveler["origin"],
    )

    expected = sorted(
        expected,
        key=lambda traveler: traveler["origin"],
    )

    return actual == expected

def flight_arguments_match(actual_args, expected_args):
    if not travelers_match(
        actual_args,
        expected_args,
    ):
        return False

    if (
        actual_args["max_stops"]
        != expected_args["max_stops"]
    ):
        return False

    if (
        actual_args["max_arrival_gap_minutes"]
        != expected_args["max_arrival_gap_minutes"]
    ):
        return False

    return True

def arguments_match(actual_trace, expected_tools):
    if len(actual_trace) != len(expected_tools):
        return False

    remaining_actual = actual_trace.copy()

    for expected_tool in expected_tools:
        expected_name = expected_tool["name"]
        expected_args = expected_tool["args"]

        matching_actual = None

        for actual_tool in remaining_actual:
            if actual_tool["name"] == expected_name:
                matching_actual = actual_tool
                break

        if matching_actual is None:
            return False

        actual_args = matching_actual["args"]

        if expected_name == "search_meetup_options":
            if not flight_arguments_match(
                actual_args,
                expected_args,
            ):
                return False
        else:
            if actual_args != expected_args:
                return False

        remaining_actual.remove(matching_actual)

    return True

def main():
    cases = load_eval_cases()
    runs_per_case = 3
    tool_passed = 0
    argument_passed = 0

    for case in cases:
        for run_number in range(1, runs_per_case + 1):
            question = case["input"]

            expected_tools = expected_tools_to_tool_calls(
                case["expected_tools"]
            )

            print("\n" + "=" * 60)
            print("CASE:", case["id"])
            print("CATEGORY:", case["category"])
            print("RUN:", run_number)
            print("=" * 60)

            answer, trace = run_tool_loop(
                question=question,
                model_with_tools=get_model_with_tools(),
                tool_map=tools_by_name,
                return_trace=True,
            )

            test_case = LLMTestCase(
                input=question,
                actual_output=answer,
                tools_called=trace_to_tool_calls(trace),
                expected_tools=expected_tools,
            )

            metric = ToolCorrectnessMetric(
                should_exact_match=True,
            )

            metric.measure(test_case)

            arguments_correct = arguments_match(
                trace,
                case["expected_tools"],
            )

            print("\nARGUMENT RESULT")
            print("---------------")
            print("Correct:", arguments_correct)
            print("\nTOOL TRACE")
            print("----------")

            for call in trace:
                print(call)

            print("\nDEEPEVAL RESULT")
            print("---------------")
            print("Score:", metric.score)
            print("Reason:", metric.reason)

            if metric.score == 1.0:
                tool_passed += 1

            if arguments_correct:
                argument_passed += 1
    total_runs = len(cases) * runs_per_case

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    print(
        f"Tool correctness: "
        f"{tool_passed}/{total_runs} "
        f"({tool_passed / total_runs:.1%})"
    )

    print(
        f"Argument correctness: "
        f"{argument_passed}/{total_runs} "
        f"({argument_passed / total_runs:.1%})"
    )


if __name__ == "__main__":
    main()
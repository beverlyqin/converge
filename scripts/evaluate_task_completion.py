import os
import json
import time
import deepeval
from deepeval.evaluate import AsyncConfig
from pathlib import Path
from dotenv import load_dotenv

from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import TaskCompletionMetric
from deepeval.models import GeminiModel
from deepeval.tracing import (
    observe,
    update_current_span,
    update_current_trace,
)
from backend.app.agent.meetup_agent import (
    get_model_with_tools,
    run_tool_loop,
    tools_by_name,
)

load_dotenv()

class TracedTool:
    def __init__(self, tool):
        self.tool = tool
        self.name = tool.name

    @observe(type="tool")
    def invoke(self, args):
        result = self.tool.invoke(args)

        update_current_span(
            name=self.name,
            input=args,
            output=result,
        )

        return result
    
@observe(type="agent")
def real_flight_agent(question: str) -> str:
    traced_tools = {
        name: TracedTool(tool)
        for name, tool in tools_by_name.items()
    }

    answer = run_tool_loop(
        question=question,
        model_with_tools=get_model_with_tools(),
        tool_map=traced_tools,
    )

    update_current_trace(
        name="Flight Meetup Agent",
        input=question,
        output=answer,
    )

    return answer


@deepeval.log_hyperparameters
def hyperparameters():
    return {
        "agent_model": "gemini-3.5-flash-lite",
        "judge_model": os.getenv(
            "DEEPEVAL_JUDGE_MODEL",
            "gemini-3.5-flash-lite",
        ),
        "task_completion_threshold": 0.7,
        "judge_async_mode": False,
        "evaluation_dispatch": "sequential",
    }

def load_task_completion_cases():
    project_root = Path(__file__).resolve().parents[1]

    cases_path = (
        project_root
        / "data"
        / "task_completion_eval_cases.json"
    )

    return json.loads(
        cases_path.read_text(encoding="utf-8")
    )

def main():
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    judge_model_name = os.getenv(
        "DEEPEVAL_JUDGE_MODEL",
        "gemini-3.5-flash-lite",
    )

    judge_model = GeminiModel(
        model=judge_model_name,
        api_key=api_key,
    )

    metric = TaskCompletionMetric(
        model=judge_model,
        threshold=0.7,
        async_mode=False,
        verbose_mode=False,
    )

    cases = load_task_completion_cases()

    dataset = EvaluationDataset(
        goldens=[
            Golden(input=case["input"])
            for case in cases
        ]
    )
    

    for index, golden in enumerate(
        dataset.evals_iterator(
            metrics=[metric],
            async_config=AsyncConfig(
                run_async=False,
            ),
        )
    ):
        if index > 0:
            print("\nWaiting 45 seconds for Gemini rate limit...")
            time.sleep(45)

        real_flight_agent(golden.input)



if __name__ == "__main__":
    main()
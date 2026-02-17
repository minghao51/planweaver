from typing import Dict, Any, Optional
from jinja2 import Environment
from pathlib import Path
import yaml

from ..models.scenario import Scenario


class TemplateEngine:
    def __init__(self, scenarios_path: Optional[str] = None):
        if scenarios_path is None:
            import os
            package_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.scenarios_path = Path(package_dir) / "scenarios"
        else:
            self.scenarios_path = Path(scenarios_path)
        self.env = Environment()
        self._scenarios: Dict[str, Scenario] = {}
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        if not self.scenarios_path.exists():
            return

        for yaml_file in self.scenarios_path.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                    scenario = Scenario(**data)
                    self._scenarios[scenario.name] = scenario
            except Exception as e:
                print(f"Warning: Failed to load scenario {yaml_file}: {e}")

    def get_scenario(self, name: str) -> Optional[Scenario]:
        return self._scenarios.get(name)

    def list_scenarios(self) -> list[str]:
        return list(self._scenarios.keys())

    def render_planner_prompt(
        self,
        scenario_name: str,
        user_intent: str,
        context: Dict[str, Any]
    ) -> str:
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return f"User Intent: {user_intent}\nContext: {context}"

        template = self.env.from_string(scenario.planner_prompt_template)
        return template.render(
            user_intent=user_intent,
            **context
        )

    def render_executor_prompt(
        self,
        scenario_name: str,
        step_task: str,
        context: Dict[str, Any]
    ) -> str:
        scenario = self._scenarios.get(scenario_name)
        if scenario is None:
            return f"Task: {step_task}\nContext: {context}"

        template = self.env.from_string(scenario.executor_template)
        return template.render(
            task=step_task,
            **context
        )

    def validate_input(
        self,
        scenario_name: str,
        input_data: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return True, []

        errors = []
        for field in scenario.input_schema.fields:
            if field.required and field.name not in input_data:
                errors.append(f"Missing required field: {field.name}")

        return len(errors) == 0, errors

    def validate_output(
        self,
        scenario_name: str,
        output: Any
    ) -> tuple[bool, list[str]]:
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return True, []

        errors = []
        for field in scenario.output_schema.fields:
            if field.required and field.name not in output:
                errors.append(f"Missing required output field: {field.name}")

        return len(errors) == 0, errors

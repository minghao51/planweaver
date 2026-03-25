"""Specialist sub-planner coordinator (Pattern 2)"""

from __future__ import annotations

import asyncio
import yaml  # type: ignore[import-untyped]
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from .llm_gateway import LLMGateway
from ..models.coordination import SubPlanFragment
from ..models.plan import ExecutionStep

logger = logging.getLogger(__name__)


class Coordinator:
    """Coordinates domain specialist sub-planners for Pattern 2: Specialist Sub-Planners"""

    def __init__(self, llm_gateway: LLMGateway, config_path: str = "config/domains.yaml"):
        self.llm = llm_gateway
        self.specialists = self._load_domain_config(config_path)

    def _load_domain_config(self, config_path: str) -> Dict[str, Any]:
        """Load domain specialist registry from YAML"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Domain config file not found at {config_path}, using empty config")
            return {}
        try:
            with open(path) as f:
                config = yaml.safe_load(f)
                return config.get("specialists", {})
        except Exception as e:
            logger.error(f"Error loading domain config from {config_path}: {e}")
            return {}

    async def coordinate_specialists(
        self,
        user_intent: str,
        domains: List[str],
        locked_constraints: Dict[str, Any],
        scenario_name: Optional[str] = None,
        planner_model: Optional[str] = None,
    ) -> List[SubPlanFragment]:
        """Run domain specialists in parallel"""
        # Decompose goal into domain-specific sub-goals
        sub_goals = await self._decompose_to_domains(user_intent, domains)

        # Run specialists in parallel (reuse scout.py async pattern)
        tasks = [
            self._run_specialist(domain, sub_goal, locked_constraints, scenario_name, planner_model)
            for domain, sub_goal in sub_goals.items()
        ]
        fragments = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_fragments = []
        for i, f in enumerate(fragments):
            if isinstance(f, Exception):
                logger.error(f"Specialist {domains[i] if i < len(domains) else 'unknown'} failed: {f}")
            elif isinstance(f, SubPlanFragment):
                valid_fragments.append(f)

        return valid_fragments

    def merge_fragments(
        self,
        fragments: List[SubPlanFragment],
    ) -> List[ExecutionStep]:
        """Merge partial DAGs without conflicts"""
        merged = []
        step_id_counter = 1

        for fragment in fragments:
            for step_data in fragment.steps:
                step = ExecutionStep(**step_data)
                step.step_id = step_id_counter
                # Renumber dependencies to maintain referential integrity
                old_deps = step.dependencies
                step.dependencies = []
                for dep in old_deps:
                    # Map old step IDs to new ones (simplified approach)
                    # In production, you'd want more sophisticated dependency tracking
                    if dep < step_id_counter:
                        step.dependencies.append(dep)
                merged.append(step)
                step_id_counter += 1

        return merged

    async def _decompose_to_domains(self, user_intent: str, domains: List[str]) -> Dict[str, str]:
        """Decompose user intent into domain-specific sub-goals"""
        sub_goals = {}
        for domain in domains:
            specialist_config = self.specialists.get(domain, {})
            system_prompt = specialist_config.get("system_prompt", "")

            # Build domain-specific sub-goal
            sub_goals[domain] = f"{user_intent}\n\nFocus: {domain.upper()}\nContext: {system_prompt}"

        return sub_goals

    async def _run_specialist(
        self,
        domain: str,
        sub_goal: str,
        locked_constraints: Dict[str, Any],
        scenario_name: Optional[str] = None,
        planner_model: Optional[str] = None,
    ) -> SubPlanFragment:
        """Run a single domain specialist"""
        specialist_config = self.specialists.get(domain, {})
        model = specialist_config.get("model", planner_model or "claude-3.5-sonnet")
        system_prompt = specialist_config.get("system_prompt", "")

        # Import here to avoid circular imports
        from .planner import Planner

        planner_instance = Planner(self.llm)

        # Generate domain-specific steps using the planner
        steps = planner_instance.decompose_into_steps(
            sub_goal,
            locked_constraints,
            scenario_name,
            model=model,
        )

        # Ensure steps is a list
        if not isinstance(steps, list):
            steps = []

        return SubPlanFragment(
            fragment_id=f"{domain}_{id(sub_goal)}",
            domain=domain,
            specialist=domain,
            steps=[s.model_dump() for s in steps],
            confidence=0.8,
            metadata={"model": model, "system_prompt": system_prompt},
        )

import click
from .orchestrator import Orchestrator
from .api.main import app
import uvicorn


@click.group()
def cli():
    """PlanWeaver - Universal LLM Planning & Execution Engine"""
    pass


@cli.command()
@click.argument("intent")
@click.option("--scenario", "-s", default=None, help="Scenario name to use")
@click.option("--planner", "-p", default="deepseek/deepseek-chat", help="Planner model")
@click.option("--executor", "-e", default="anthropic/claude-3-5-sonnet-20241022", help="Executor model")
def plan(intent: str, scenario: str, planner: str, executor: str):
    """Start an interactive planning session"""
    orchestrator = Orchestrator(
        planner_model=planner,
        executor_model=executor
    )

    plan = orchestrator.start_session(intent, scenario)
    click.echo(f"Session created: {plan.session_id}")
    click.echo(f"Status: {plan.status.value}")

    if plan.open_questions:
        click.echo("\nClarifying Questions:")
        for q in plan.open_questions:
            click.echo(f"  - {q.question}")

        answers = {}
        for q in plan.open_questions:
            if not q.answered:
                answer = click.prompt(f"\n{q.question}", default="")
                answers[q.id] = answer

        if answers:
            plan = orchestrator.answer_questions(plan, answers)

    proposals = orchestrator.get_strawman_proposals(plan)
    if proposals:
        click.echo("\nProposed Approaches:")
        for i, p in enumerate(proposals, 1):
            click.echo(f"\n{i}. {p['title']}")
            click.echo(f"   {p['description']}")
            click.echo(f"   Pros: {', '.join(p['pros'][:2])}")
            click.echo(f"   Cons: {', '.join(p['cons'][:2])}")

        if click.confirm("\nApprove this plan?"):
            orchestrator.approve_plan(plan)
            click.echo("Plan approved!")

            result = orchestrator.execute(plan)
            click.echo(f"\nExecution completed: {result.status.value}")

            if result.final_output:
                click.echo("\nFinal Output:")
                click.echo(result.final_output)


@cli.command()
@click.argument("session_id")
@click.option("--executor", "-e", default="anthropic/claude-3-5-sonnet-20241022", help="Executor model")
def execute(session_id: str, executor: str):
    """Execute an approved plan"""
    orchestrator = Orchestrator(executor_model=executor)
    plan = orchestrator.get_session(session_id)

    if not plan:
        click.echo(f"Session {session_id} not found")
        return

    if plan.status.value != "APPROVED":
        click.echo(f"Plan must be APPROVED first (current: {plan.status.value})")
        return

    result = orchestrator.execute(plan)
    click.echo(f"Execution completed: {result.status.value}")


@cli.command()
def serve():
    """Start the PlanWeaver API server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    cli()

from planweaver.services.template_engine import TemplateEngine


def test_template_engine_loads_nested_scenarios():
    engine = TemplateEngine("data/scenarios")

    scenarios = set(engine.list_scenarios())

    assert "Blog Post Generation" in scenarios
    assert "Code Refactoring" in scenarios
    assert "API Development" not in scenarios  # Only loads root .yaml, not subdirectories


def test_template_engine_excludes_template_scaffolding():
    engine = TemplateEngine("data/scenarios")

    scenarios = set(engine.list_scenarios())

    assert "Your Scenario Name" not in scenarios

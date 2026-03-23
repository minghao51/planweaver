# Scenarios Documentation

Scenarios in PlanWeaver define templates for different types of planning tasks. They provide structure for AI planning and execution by specifying prompts, input/output schemas, and validation rules.

## Scenario Format

Each scenario is a YAML file with the following structure:

```yaml
name: "Scenario Name"
description: "Brief description of what this scenario does"

planner_prompt_template: |
  Template for the planning phase. Available variables:
  - {user_intent}: The user's goal
  - {context}: Additional context from input_schema

executor_template: |
  Template for executing individual steps. Available variables:
  - {task}: The specific step task
  - {context}: Additional context from input_schema

input_schema:
  fields:
    - name: field_name
      type: string|number|array|object|boolean
      description: What this field is for
      required: true|false
      default: default_value

output_schema:
  type: object
  fields:
    - name: output_field
      type: string
      description: Expected output format
```

## Available Scenarios

### Blog Post Generation
- **File**: `blog_generation.yaml`
- **Purpose**: Generate blog post series based on keywords and topics
- **Inputs**: topic, keywords, tone, target_audience
- **Outputs**: title, content, meta_description

### Code Refactoring
- **File**: `code_refactoring.yaml`
- **Purpose**: Refactor code for better quality and maintainability
- **Inputs**: code, goals, language
- **Outputs**: refactored_code, explanation, changes_made

### Data Analysis
- **File**: `data_analysis.yaml`
- **Purpose**: Analyze data and generate insights
- **Inputs**: data_description, analysis_goals, dataset_info
- **Outputs**: insights, visualizations, recommendations

### Market Analysis
- **File**: `market_analysis.yaml`
- **Purpose**: Analyze market trends and competition
- **Inputs**: industry, focus_areas, competitors
- **Outputs**: trends, opportunities, threats, recommendations

## Creating New Scenarios

1. Copy the template from `templates/template.yaml` to a new YAML file in the `scenarios/` directory
2. Fill in the name, description, and templates
3. Define input and output schemas
4. Test your scenario by creating a new plan with it

## Scenario Template

A template is available at `templates/template.yaml` with the following structure:

```yaml
name: "Your Scenario Name"
description: "What this scenario does"

planner_prompt_template: |
  You are an expert in [domain]. Analyze the following request:

  User Request: {user_intent}

  Additional Context:
  - Field 1: {field1}
  - Field 2: {field2}

  Create a detailed plan to accomplish this goal.

executor_template: |
  Task: {task}

  Context:
  - Field 1: {field1}
  - Field 2: {field2}

  Execute this task according to the plan.

input_schema:
  fields:
    - name: field1
      type: string
      description: Description of field1
      required: true
    - name: field2
      type: array
      description: Description of field2
      required: false

output_schema:
  type: object
  fields:
    - name: result
      type: object
      description: The main result
```

## Best Practices

1. **Be Specific**: Clear, focused scenarios work better than generic ones
2. **Use Variables**: Reference input fields in templates using `{field_name}` syntax
3. **Validate Inputs**: Mark important fields as required
4. **Define Outputs**: Specify what the executor should produce
5. **Test Iteratively**: Try scenarios with real inputs and refine based on results

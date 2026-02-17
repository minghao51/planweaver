from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum


class SchemaType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    MARKDOWN_TABLE = "markdown_table"


class SchemaField(BaseModel):
    name: str
    type: SchemaType
    description: str
    required: bool = True
    default: Optional[Any] = None


class InputSchema(BaseModel):
    fields: List[SchemaField] = Field(default_factory=list)

    def get_template_vars(self) -> Dict[str, Any]:
        return {f.name: f.default for f in self.fields if f.default is not None}


class OutputSchema(BaseModel):
    type: SchemaType = SchemaType.STRING
    fields: List[SchemaField] = Field(default_factory=list)

    def validate_output(self, output: Any) -> bool:
        if output is None:
            return False
        
        if self.type == SchemaType.STRING:
            return isinstance(output, str) and len(output) > 0
        
        if self.type == SchemaType.ARRAY:
            return isinstance(output, list)
        
        if self.type == SchemaType.OBJECT:
            return isinstance(output, dict)
        
        if self.type == SchemaType.INTEGER:
            return isinstance(output, int)
        
        if self.type == SchemaType.FLOAT:
            return isinstance(output, (int, float))
        
        if self.type == SchemaType.BOOLEAN:
            return isinstance(output, bool)
        
        if self.fields:
            if not isinstance(output, dict):
                return False
            for field in self.fields:
                if field.required and field.name not in output:
                    return False
            return True
        
        return True


class Scenario(BaseModel):
    name: str
    description: str
    planner_prompt_template: str
    executor_template: str
    input_schema: InputSchema = Field(default_factory=InputSchema)
    output_schema: OutputSchema = Field(default_factory=OutputSchema)
    default_planner_model: str = "deepseek/deepseek-chat"
    default_executor_model: str = "anthropic/claude-3-5-sonnet-20241022"

    def get_input_vars(self) -> Dict[str, Any]:
        return self.input_schema.get_template_vars()

    def get_output_fields(self) -> List[str]:
        return [f.name for f in self.output_schema.fields]

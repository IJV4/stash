from stash.llm import frozen_schema

SCHEMA_NAME = "prep_steps"

STEPS_SCHEMA = frozen_schema(
    {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "lead_days": {"type": "integer"},
                    },
                    "required": ["text", "lead_days"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["steps"],
        "additionalProperties": False,
    }
)

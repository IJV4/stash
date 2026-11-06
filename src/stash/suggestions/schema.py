from stash.llm import frozen_schema

SCHEMA_NAME = "suggestions"

SUGGESTIONS_SCHEMA = frozen_schema(
    {
        "type": "object",
        "properties": {
            "picks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["item_id", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["picks"],
        "additionalProperties": False,
    }
)

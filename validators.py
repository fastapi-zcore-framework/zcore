import jsonschema
from jsonschema import validate
from app.core.exception.exceptions import ValidationError

def validate_json_schema(data: dict, schema: dict):
    if data is None:
        return
    try:
        validate(instance=data, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        raise ValidationError(
            message=f"JSON Schema validation failed: {e.message}",
            payload={"path": list(e.path), "schema": e.schema}
        )
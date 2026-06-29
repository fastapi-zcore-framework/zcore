from jsonschema import validate, Draft7Validator, exceptions

from app.core.exception.exceptions import ValidationError

def validate_json_schema(data: dict, schema: dict = None):
    if data is None:
        return
    try:
        if schema is None:
            Draft7Validator.check_schema(data)
        else:
            validate(instance=data, schema=schema)
    except exceptions.ValidationError as e:
        raise ValidationError(
            message=f"JSON Schema validation failed: {e.message}",
            payload={"path": list(e.path), "schema": e.schema}
        )
    except exceptions.SchemaError as e:
        raise ValidationError(
            message="Internal System Error: The defined schema is corrupted or invalid.",
            payload={"error": e.message}
        )
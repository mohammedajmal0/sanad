"""The system prompt lives in the MLflow Prompt Registry (Unity Catalog); this repo holds its source.

Register a new version from customer_service.md and point @production at it:
    cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python -m agent.prompt
"""

from pathlib import Path

import mlflow

NAME = "sanad.prompts.customer_service"  # its own schema: deploy grants the app MANAGE there
URI = f"prompts:/{NAME}@production"
SOURCE = Path(__file__).parent / "prompts" / "customer_service.md"


def load_system_prompt() -> str:
    """The @production version. Fails loudly: a silent fallback would hide which prompt ran."""
    mlflow.set_registry_uri("databricks-uc")
    return mlflow.genai.load_prompt(URI).template


def register() -> int:
    mlflow.set_registry_uri("databricks-uc")
    version = mlflow.genai.register_prompt(
        name=NAME, template=SOURCE.read_text(), commit_message="from agent/agent/prompts"
    ).version
    mlflow.genai.set_prompt_alias(NAME, alias="production", version=version)
    return version


if __name__ == "__main__":
    print(f"{NAME} v{register()} is @production")

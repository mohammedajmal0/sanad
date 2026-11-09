"""System prompts live in the MLflow Prompt Registry (Unity Catalog); this repo holds their source,
one prompts/<name>.md per agent, registered as sanad.prompts.<name>.

Register a new version and point @production at it (all prompts, or the ones named):
    cd agent && DATABRICKS_CONFIG_PROFILE=sanad uv run python -m agent.prompt [supervisor ...]
"""

import sys
from pathlib import Path

import mlflow

SCHEMA = "sanad.prompts"  # its own schema: deploy grants the app MANAGE there
PROMPTS = Path(__file__).parent / "prompts"
CUSTOMER_SERVICE, SUPERVISOR = "customer_service", "supervisor"


def load_system_prompt(name: str) -> str:
    """The @production version. Fails loudly: a silent fallback would hide which prompt ran."""
    mlflow.set_registry_uri("databricks-uc")
    return mlflow.genai.load_prompt(f"prompts:/{SCHEMA}.{name}@production").template


def register(name: str) -> int:
    mlflow.set_registry_uri("databricks-uc")
    version = mlflow.genai.register_prompt(
        name=f"{SCHEMA}.{name}",
        template=(PROMPTS / f"{name}.md").read_text(),
        commit_message="from agent/agent/prompts",
    ).version
    mlflow.genai.set_prompt_alias(f"{SCHEMA}.{name}", alias="production", version=version)
    return version


if __name__ == "__main__":
    for name in sys.argv[1:] or sorted(p.stem for p in PROMPTS.glob("*.md")):
        print(f"{SCHEMA}.{name} v{register(name)} is @production")

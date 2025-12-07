"""Update .env.{ENV} file with values from Terraform outputs."""

import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Update Output to Env")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


env_var_template = {
    "Azure Search": {
        "AZURE_SEARCH_ENDPOINT": None,
        "AZURE_AI_SEARCH_INDEX_NAME": None,
        "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY": None,
    },
    "Azure OpenAI": {
        "AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT": "text-embedding-3-large",
        "AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION": "2024-12-01-preview",
        "AZURE_OPENAI_CHAT_DEPLOYMENT": "gpt-4.1",
        "AZURE_OPENAI_CHAT_API_VERSION": "2024-12-01-preview",
        "AZURE_OPENAI_ENDPOINT": None,
        "AZURE_OPENAI_VECTORIZER_ENDPOINT": None,
        "AZURE_OPENAI_PRIMARY_KEY": None,
    },
    "Azure Storage": {
        "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING": None,
        "AZURE_CONTAINER_STORAGE_NAME": "kioskbot-logs",
    },
    "Azure Container Registry": {"AZURE_CONTAINER_REGISTRY_LOGIN_SERVER": None},
    "Kafka": {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_TOPIC": "chatbot_logs",
    },
    "Rest API Application and Middleware": {
        "APP_TITLE": "Information Kiosk Bot",
        "APP_DESCRIPTION": "Endpoints for the Information Kiosk Bot",
        "DOCS_URL": "/docs",
        "REDOC_URL": "/redoc",
        "FRONTEND_URL": "http://localhost:5173",
        "BACKEND_URL": "http://localhost:8000/",
        "ALLOWED_CREDENTIALS": "True",
        "ALLOWED_METHODS": '["GET","POST","PUT","DELETE"]',
        "ALLOWED_HEADERS": '["*"]',
    },
    "LangSmith": {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com",
        "LANGSMITH_API_KEY": "your-langsmith-api-key",
        "LANGSMITH_PROJECT": "kioskbot-dev",
    },
}


def escape_env_value(value: str) -> str:
    """Normalize Windows newlines, escape backslashes, quotes, and dollar signs."""
    return (
        value.replace("\r", "")
        .replace("\\", r"\\")
        .replace('"', r"\"")
        .replace("$", r"\$")
    )


def read_kv_file(path: str) -> dict:
    """Read simple KEY=VALUE lines; ignore comments and malformed lines."""
    if not Path(path).exists():
        logger.error("Error: File not found: %s", path)
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)
    vars_map = {}
    with Path(path).open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                # ignore non key=value (e.g., multiline YAML continuation)
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            vars_map[key] = value
    return vars_map


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update .env.{ENV} file with values from Terraform outputs"
    )
    parser.add_argument(
        "-e", "--env", required=True, help="Environment name (e.g., dev, prod)"
    )
    return parser.parse_args()


def update_env_vars(env_vars: dict, global_vars: dict, env: str) -> dict:
    """Update the environment variables."""
    updated_env_vars = {}
    for segment, segment_dict in env_var_template.items():
        updated_env_vars["segment_" + segment] = segment
        if segment == "LangSmith":
            logger.info(
                "\n\nREMINDER!! Update LANGSMITH_API_KEY in .env.%s\n\n",
                env,
            )
            updated_env_vars |= dict(segment_dict)
        elif segment in ["Rest API Application and Middleware", "Kafka"]:
            updated_env_vars |= dict(segment_dict)
        else:
            for key, value in segment_dict.items():
                if segment_dict.get(key) is None:
                    if key in env_vars:
                        updated_env_vars[key] = env_vars[key]
                    elif key in global_vars:
                        updated_env_vars[key] = global_vars[key]
                    else:
                        logger.error("Error: %s skipped, not found anywhere", key)
                else:
                    updated_env_vars[key] = value
    return updated_env_vars


def write_env_vars(env_vars: dict, out_path: str) -> None:
    """Write the environment variables to the .env.{ENV} file."""
    with Path(out_path).open("w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            if key.startswith("segment_"):
                f.write(f"\n#{value}\n")
            else:
                quoted = escape_env_value(str(value))
                f.write(f'{key}="{quoted}"\n')


def main() -> None:
    """Update the .env.{ENV} file with values from Terraform outputs."""
    args = parse_args()
    env = args.env
    env_output_file = f"scripts/terraform/azure/outputs/{env}.output"
    logger.info("\n\nUpdating .env.%s file with values from Terraform outputs\n\n", env)
    global_output_file = "scripts/terraform/azure/outputs/global.output"
    try:
        global_vars = read_kv_file(global_output_file)
        env_vars = read_kv_file(env_output_file)
    except FileNotFoundError:
        logger.exception("Error while reading Terraform output files")
        raise
    updated_env_vars = update_env_vars(env_vars, global_vars, env)
    write_env_vars(updated_env_vars, f".env.{env}")


if __name__ == "__main__":
    main()

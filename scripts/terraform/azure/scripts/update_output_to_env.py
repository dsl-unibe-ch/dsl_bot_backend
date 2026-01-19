"""Update .env.{ENV} file with values from Terraform outputs."""

import argparse
import json
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


def escape_env_value(value: str) -> str:
    """Normalize Windows newlines, escape backslashes, quotes, and dollar signs."""
    return (
        value.replace("\r", "")
        .replace("\\", r"\\")
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
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith(("[", "{")):  # Try to parse JSON values (lists/dicts)
                try:
                    value = json.loads(value)
                except json.JSONDecodeError as err:
                    logger.exception(
                        "Error: %s is not a valid JSON value: %s", key, value
                    )
                    error_message = f"Error: {key} is not a valid JSON value: {value}"
                    raise ValueError(error_message) from err
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


def update_env_vars(
    env_vars: dict, global_vars: dict, env: str, env_vars_template: dict
) -> dict:
    """Update the environment variables."""
    updated_env_vars = {}
    for key, value in env_vars_template.items():
        if key == "LANGSMITH_API_KEY":
            logger.info(
                "\n\nREMINDER!! Update LANGSMITH_API_KEY in .env.%s\n\n",
                env,
            )
        if key == "BACKEND_URL":
            if key in env_vars and env_vars[key] is not None and len(env_vars[key])>5:
                updated_env_vars[key] = env_vars[key]
            elif key in global_vars:
                updated_env_vars[key] = global_vars[key]
            else:
                updated_env_vars[key] = value
                logger.warning("Warning: %s assigned a default value, not found in Terraform outputs", key)
            
        elif not key.startswith("AZURE"):
            updated_env_vars[key] = value
        elif key in env_vars:
            updated_env_vars[key] = env_vars[key]
        elif key in global_vars:
            updated_env_vars[key] = global_vars[key]
        else:
            logger.error("Error: %s skipped, not found anywhere", key)
    return updated_env_vars


def write_env_vars(env_vars: dict, out_path: str) -> None:
    """Write the environment variables to the .env.{ENV} file."""
    with Path(out_path).open("w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            if isinstance(value, (list, dict)):
                rendered = json.dumps(value, separators=(",", ":"))
            elif value in [
                "Information Kiosk Bot",
                "Endpoints for the Information Kiosk Bot",
            ]:
                rendered = f'"{value}"'
            else:
                rendered = escape_env_value(str(value))
            f.write(f"\n{key}={rendered}\n")


def main() -> None:
    """Update the .env.{ENV} file with values from Terraform outputs."""
    args = parse_args()
    env = args.env
    env_vars_template_file = f".env.{env}.example"
    env_output_file = f"scripts/terraform/azure/outputs/{env}.output"
    logger.info("\n\nUpdating .env.%s file with values from Terraform outputs\n\n", env)
    global_output_file = "scripts/terraform/azure/outputs/global.output"
    try:
        env_vars_template = read_kv_file(env_vars_template_file)
        global_vars = read_kv_file(global_output_file)
        env_vars = read_kv_file(env_output_file)
    except FileNotFoundError:
        logger.exception("Error while reading Terraform output files")
        raise
    updated_env_vars = update_env_vars(env_vars, global_vars, env, env_vars_template)
    write_env_vars(updated_env_vars, f".env.{env}")


if __name__ == "__main__":
    main()

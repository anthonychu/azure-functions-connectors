"""Environment variable resolution for connector trigger configuration."""

import os
import re

# %VAR_NAME% — Azure Functions app-setting convention
_PERCENT_PATTERN = re.compile(r"^%([^%]+)%$")

# $VAR_NAME — shell-style, uppercase + underscore only (avoids OData like $filter)
_DOLLAR_PATTERN = re.compile(r"^\$([A-Z_][A-Z0-9_]*)$")


def resolve_value(value: str) -> str:
    """Resolve a single configuration value that may reference an environment variable.

    Supported formats:
      %VAR_NAME%  — Azure Functions convention
      $VAR_NAME   — shell-style (only uppercase letters, digits, underscore)
      anything else — returned as a literal
    """
    m = _PERCENT_PATTERN.match(value)
    if m:
        var_name = m.group(1)
        try:
            return os.environ[var_name]
        except KeyError:
            raise ValueError(
                f"Environment variable '{var_name}' referenced in '%{var_name}%' is not set"
            )

    m = _DOLLAR_PATTERN.match(value)
    if m:
        var_name = m.group(1)
        try:
            return os.environ[var_name]
        except KeyError:
            raise ValueError(
                f"Environment variable '{var_name}' referenced in '${var_name}' is not set"
            )

    return value


def resolve_config(
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict,
) -> tuple[str, str, dict]:
    """Resolve environment variable references in all config values."""
    return (
        resolve_value(connection_id),
        resolve_value(trigger_path),
        {k: resolve_value(v) for k, v in trigger_queries.items()},
    )

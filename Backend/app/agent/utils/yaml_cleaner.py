import re
import logging
import yaml
from typing import Any

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    'password', 'secret', 'token', 'api_key', 'apikey',
    'access_key', 'private_key', 'auth', 'authorization',
    'bearer', 'credentials', 'pass', 'pwd', 'secret_key',
    'app_key', 'client_secret', 'client_id', 'service_account',
    'account_key', 'PAT', 'GITHUB_TOKEN', 'DOCKER_TOKEN', 'GITLAB_TOKEN'
}

REDACTED = "<REDACTED>"

SECRET_KEY_SUBSTRINGS = {'secret', 'token', 'key', 'pass', 'auth', 'cred'}


def redact_secrets(content: str) -> str:
    try:
        data = yaml.safe_load(content)
        if data is None:
            return content
        cleaned = _recursive_clean(data)
        return yaml.dump(cleaned, default_flow_style=False, indent=2)
    except yaml.YAMLError as e:
        logger.warning("YAML parsing failed, falling back to regex redaction: %s", e)
        return _clean_with_regex(content)


def _recursive_clean(obj: Any, parent_key: str = "") -> Any:
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if _is_sensitive_key(key):
                result[key] = _redact_value(value)
            else:
                result[key] = _recursive_clean(value, parent_key=key)
        return result
    elif isinstance(obj, list):
        return [_recursive_clean(item, parent_key) for item in obj]
    elif isinstance(obj, str):
        return _redact_inline_secrets(obj)
    else:
        return obj


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    return key in SENSITIVE_KEYS or any(s in key_lower for s in SECRET_KEY_SUBSTRINGS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return REDACTED
    elif isinstance(value, (int, float)):
        return REDACTED
    elif isinstance(value, list):
        return [REDACTED for _ in value]
    elif isinstance(value, dict):
        return {k: REDACTED for k in value}
    return REDACTED


def _redact_inline_secrets(value: str) -> str:

    if re.search(r'\$\{\{?\s*secrets\.\w+\s*\}?\}', value):
        return value

    if re.match(r'^\$[A-Z_][A-Z0-9_]*$', value):
        return value

    if re.match(r'^[a-zA-Z0-9+/=_\-]{32,}$', value):
        return REDACTED
    return value


def _clean_with_regex(content: str) -> str:

    patterns = [
        (r'(?i)((?:token|key|secret|password|auth|bearer|credential|pat)'
         r'\s*[:=]\s*)[\'"]?[^\s\'"#>|{}\[\]]+[\'"]?',
         r'\1"<REDACTED>"'),

        (r'[\'"]([a-zA-Z0-9+/=_\-]{32,})[\'"]', '"<REDACTED>"'),

        (r'(\benv\b.*?[:=]\s*)(?!\$)[^\s#]+', r'\1<REDACTED>'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content
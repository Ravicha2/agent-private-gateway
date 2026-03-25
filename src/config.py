"""Configuration management for the LLM Gateway."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class GatewayConfig(BaseSettings):
    """Configuration settings for the LLM Gateway."""

    model_config = ConfigDict(env_prefix="GATEWAY_")

    ollama_url: str = "http://localhost:11434"
    sensitive_data_path: str = "/app/sensitive_data.json"
    log_level: str = "INFO"
    max_request_size: int = 1024 * 1024  # 1MB
    token_prefix: str = "[TOKEN"
    token_suffix: str = "]"
    enable_regex_patterns: bool = True
    enable_system_prompt_injection: bool = True
    strict_detokenization: bool = False  # Fail on unmapped tokens?
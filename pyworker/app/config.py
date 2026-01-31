"""Configuration management using pydantic-settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=7788, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # AI CLI Configuration
    default_ai_cli: str = Field(default="claude", description="Default AI CLI to use")
    enabled_ai_clis: str = Field(default="claude,opencode", description="Enabled AI CLIs (comma separated)")

    # Claude Code Configuration
    claude_binary: str = Field(default="claude", description="Claude binary path")
    claude_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    claude_model: Optional[str] = Field(default="claude-3-5-sonnet-20241022", description="Claude model")

    # OpenCode Configuration
    opencode_binary: str = Field(default="opencode", description="OpenCode binary path")
    opencode_api_key: Optional[str] = Field(default=None, description="OpenCode API key")
    opencode_api_base: Optional[str] = Field(default="https://api.opencode.com", description="OpenCode API base URL")
    opencode_model: Optional[str] = Field(default="gpt-4", description="OpenCode model")

    # Worker Configuration
    workers_base_dir: str = Field(default="./data/workers", description="Base directory for worker data")
    max_workers: int = Field(default=10, description="Maximum number of workers")
    worker_timeout: int = Field(default=300, description="Worker timeout in seconds")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_file: str = Field(default="./logs/app.log", description="Log file path")

    def get_enabled_ai_clis(self) -> List[str]:
        """Get list of enabled AI CLIs."""
        return [cli.strip() for cli in self.enabled_ai_clis.split(",") if cli.strip()]

    def get_ai_cli_config(self, ai_cli_type: str) -> dict:
        """Get configuration for a specific AI CLI."""
        if ai_cli_type == "claude":
            config = {
                "binary": self.claude_binary,
                "model": self.claude_model,
            }
            # Only add api_key if it's not None
            if self.claude_api_key:
                config["api_key"] = self.claude_api_key
            return config
        elif ai_cli_type == "opencode":
            config = {
                "binary": self.opencode_binary,
                "api_base": self.opencode_api_base,
                "model": self.opencode_model,
            }
            # Only add api_key if it's not None
            if self.opencode_api_key:
                config["api_key"] = self.opencode_api_key
            return config
        else:
            raise ValueError(f"Unknown AI CLI type: {ai_cli_type}")


# Global settings instance
settings = Settings()

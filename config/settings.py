"""Configuration management for Ethos using Pydantic Settings."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Slack Configuration
    SLACK_BOT_TOKEN: str = Field(..., description="Slack bot token (xoxb-...)")
    SLACK_APP_TOKEN: str = Field(..., description="Slack app token (xapp-...)")
    
    # AI Model Configuration
    GITHUB_TOKEN: Optional[str] = Field(None, description="GitHub token for GitHub Models API")
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    MODEL_NAME: str = Field(default="gpt-4o", description="LLM model name")
    TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0, description="LLM temperature")
    
    # Vector Database Configuration
    FAISS_INDEX_PATH: str = Field(default="./data/faiss_index", description="Path to FAISS index")
    MESSAGES_FILE: str = Field(default="./data/slack_messages.json", description="Path to messages file")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model")
    
    # Application Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment (development/production)")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    MAX_MESSAGES: int = Field(default=10000, gt=0, description="Maximum messages to fetch")
    
    # RAG Configuration
    CHUNK_SIZE: int = Field(default=500, gt=0, description="Text chunk size")
    CHUNK_OVERLAP: int = Field(default=50, ge=0, description="Text chunk overlap")
    TOP_K_RESULTS: int = Field(default=10, gt=0, description="Number of results to retrieve")
    
    # Priority Channel Configuration
    PRIORITY_CHANNELS: list = Field(
        default=[
            "leadership",
            "management", 
            "executives",
            "all-hands",
            "announcements",
            "important"
        ],
        description="Channels with high priority for search results"
    )
    PRIORITY_BOOST_FACTOR: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Score boost for priority channel messages (0.0-1.0)"
    )
    
    # Performance Configuration
    MAX_QUERY_LENGTH: int = Field(default=500, gt=0, description="Maximum query length")
    RATE_LIMIT_PER_MINUTE: int = Field(default=10, gt=0, description="Rate limit per user")
    LLM_TIMEOUT: int = Field(default=30, gt=0, description="LLM timeout in seconds")
    
    @validator("SLACK_BOT_TOKEN")
    def validate_bot_token(cls, v):
        """Validate Slack bot token format."""
        if not v.startswith("xoxb-"):
            raise ValueError("SLACK_BOT_TOKEN must start with 'xoxb-'")
        return v
    
    @validator("SLACK_APP_TOKEN")
    def validate_app_token(cls, v):
        """Validate Slack app token format."""
        if not v.startswith("xapp-"):
            raise ValueError("SLACK_APP_TOKEN must start with 'xapp-'")
        return v
    
    @validator("GITHUB_TOKEN")
    def validate_github_token(cls, v):
        """Validate GitHub token format if provided."""
        if v and not (v.startswith("ghp-") or v.startswith("github_pat_")):
            raise ValueError("GITHUB_TOKEN must start with 'ghp-' or 'github_pat_'")
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format if provided."""
        if v and not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with 'sk-'")
        return v
    
    def validate_ai_config(self) -> bool:
        """Ensure at least one AI provider is configured."""
        if not self.GITHUB_TOKEN and not self.OPENAI_API_KEY:
            raise ValueError("Either GITHUB_TOKEN or OPENAI_API_KEY must be provided")
        return True
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Validate AI configuration on import
settings.validate_ai_config()

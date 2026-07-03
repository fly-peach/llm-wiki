"""LLM Wiki API — 全局配置（Pydantic Settings）"""

from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录（api/..）
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置，自动从 .env 文件和环境变量读取"""

    # 工作区
    workspace_path: str = "."

    # 数据目录（存储注册表、缓存等，默认项目根下的 .llmwiki）
    data_dir: str = str(ROOT_DIR / ".llmwiki")

    # PDF
    pdf_backend: str = "opendataloader"  # 'opendataloader' | 'mistral'
    mistral_api_key: str = ""

    # Embedding
    voyage_api_key: str = ""
    embedding_model: str = "voyage-4-lite"

    # 运行环境
    stage: str = "dev"  # 'dev' | 'prod'

    # 前端地址（CORS）
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

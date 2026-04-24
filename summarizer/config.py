from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import torch


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    default_model: str = "sshleifer/distilbart-cnn-12-6"
    device: Literal["cuda", "cpu", "auto"] = "auto"

    max_input_length: int = 1024
    max_output_length: int = 256
    min_output_length: int = 50
    num_beams: int = 4
    length_penalty: float = 2.0
    no_repeat_ngram_size: int = 3

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def resolved_device(self) -> str:
        if self.device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.device


settings = Settings()

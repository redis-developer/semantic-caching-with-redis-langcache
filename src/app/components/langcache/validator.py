from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError


class AskQuestionBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) == 0:
            raise PydanticCustomError("question", "Question must not be empty")

        return normalized


class AskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    question: str
    answer: str
    cache_hit: bool = Field(serialization_alias="cacheHit")
    source: Literal["cache", "fallback"]
    matched_prompt: str | None = Field(
        default=None,
        serialization_alias="matchedPrompt",
    )
    similarity: float = 0.0
    cache_key: str = Field(serialization_alias="cacheKey")
    ttl_seconds: int = Field(serialization_alias="ttlSeconds")
    hit_count: int = Field(serialization_alias="hitCount")


class CacheStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    requests: int
    hits: int
    misses: int
    entries: int
    hit_rate: float = Field(serialization_alias="hitRate")

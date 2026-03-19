from __future__ import annotations

import hashlib
import math
import re

VECTOR_DIMENSIONS = 32
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")

TOKEN_NORMALIZATION: dict[str, str] = {
    "change": "reset",
    "forgot": "reset",
    "recover": "reset",
    "update": "reset",
    "login": "password",
    "passcode": "password",
    "pin": "password",
    "invoice": "billing",
    "payment": "billing",
    "receipt": "billing",
    "refund": "billing",
    "shipping": "shipping",
    "delivery": "shipping",
    "package": "shipping",
    "parcel": "shipping",
    "close": "delete",
    "delete": "delete",
    "remove": "delete",
}


def normalize_token(token: str) -> str:
    return TOKEN_NORMALIZATION.get(token, token)


def tokenize(text: str) -> list[str]:
    return [normalize_token(token) for token in TOKEN_PATTERN.findall(text.lower())]


def embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_DIMENSIONS

    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_DIMENSIONS
        vector[index] += 1.0

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have the same length")

    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return dot_product / (left_magnitude * right_magnitude)


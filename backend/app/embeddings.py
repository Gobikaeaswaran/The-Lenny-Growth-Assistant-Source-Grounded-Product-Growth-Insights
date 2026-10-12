import hashlib
import re
from collections import Counter

from app.config import get_settings


def embed_text(text: str) -> list[float]:
    """Create a deterministic hashed token vector for a no-extra-model demo baseline."""
    dimensions = get_settings().embedding_dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
    counts = Counter(features)
    vector = [0.0] * dimensions
    for feature, count in counts.items():
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign * (1.0 + (count - 1) * 0.3)
    norm = sum(value * value for value in vector) ** 0.5
    return [value / norm for value in vector] if norm else vector
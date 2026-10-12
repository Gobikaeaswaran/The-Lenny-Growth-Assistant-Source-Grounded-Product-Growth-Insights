import re

from app.schemas import Artifact


def make_artifact(content: str, title: str = "Assistant artifact") -> Artifact | None:
    html = re.search(r"```html\s*([\s\S]*?)```", content, re.IGNORECASE)
    if html:
        return Artifact(type="html", title=title, content=html.group(1).strip())
    code = re.search(r"```([a-zA-Z0-9_+-]+)\s*([\s\S]*?)```", content)
    if code:
        return Artifact(type="code", title=title, content=code.group(2).strip())
    return Artifact(type="markdown", title=title, content=content.strip()) if content.strip() else None


def sanitize_html(content: str) -> str:
    """Server-side defense-in-depth sanitizer; browser uses an opaque sandbox too."""
    content = re.sub(r"(?is)<\s*(script|iframe|object|embed|form|base|meta|link)\b[^>]*>.*?<\s*/\s*\1\s*>", "", content)
    content = re.sub(r"(?is)<\s*(script|iframe|object|embed|form|base|meta|link)\b[^>]*/\s*>", "", content)
    content = re.sub(r"(?is)\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", content)
    content = re.sub(r"(?is)(href|src|action)\s*=\s*([\"'])\s*javascript:[\s\S]*?\2", r"\1=\2#\2", content)
    return content
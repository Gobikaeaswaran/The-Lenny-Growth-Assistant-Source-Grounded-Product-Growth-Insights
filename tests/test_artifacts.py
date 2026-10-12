from app.artifacts import make_artifact, sanitize_html


def test_sanitizer_removes_scripts_event_handlers_and_javascript_urls():
    html = '<div onclick="alert(1)"><script>alert(1)</script><a href="javascript:alert(1)">open</a><p onload=alert(2)>safe text</p></div>'
    cleaned = sanitize_html(html)
    assert "<script" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "onload" not in cleaned.lower()
    assert "javascript:" not in cleaned.lower()
    assert "safe text" in cleaned


def test_artifact_extractor_preserves_html_payload():
    artifact = make_artifact("Here is the result:\n```html\n<h1>Hello</h1>\n```")
    assert artifact is not None
    assert artifact.type == "html"
    assert artifact.content == "<h1>Hello</h1>"
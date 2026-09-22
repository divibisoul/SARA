import base64
import json

from sara.research import neural_lens


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_neural_lens_local_extract_retains_compatibility():
    lens = neural_lens.NeuralLens()
    structure = lens.extract("def alpha(x):\n    return x\n")
    assert structure.functions == ["alpha"]
    assert structure.revision is None
    assert structure.source_sha is None


def test_neural_lens_remote_scan_preserves_ref_and_git_blob_sha(monkeypatch):
    source = "def alpha(x):\n    return x\n"
    payload = {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode(source.encode()).decode(),
        "sha": "blob-sha-123",
    }

    def fake_urlopen(request, timeout=20):
        assert "?ref=main" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(neural_lens.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    lens = neural_lens.NeuralLens()
    structure = lens.extract_from_repo(
        "https://github.com/divibisoul/SARA",
        "src/sara/core/ara.py",
        ref="main",
    )
    assert structure.functions == ["alpha"]
    assert structure.revision == "main"
    assert structure.source_sha == "blob-sha-123"

import json
from pathlib import Path


def test_openclaw_plugin_manifest_and_package():
    plugin_root = Path(__file__).resolve().parents[1] / "openclaw_plugin"
    package_json = json.loads((plugin_root / "package.json").read_text(encoding="utf-8"))
    manifest = json.loads((plugin_root / "openclaw.plugin.json").read_text(encoding="utf-8"))
    source = (plugin_root / "index.js").read_text(encoding="utf-8")

    assert package_json["openclaw"]["extensions"] == ["./index.js"]
    assert manifest["id"] == "agentcrew"
    assert "configSchema" in manifest
    assert "definePluginEntry" in source
    assert "registerTool" in source

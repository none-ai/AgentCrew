"""
Registries and installers for skills and MCP servers.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..runtime import get_runtime_paths


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return cleaned or "item"


@dataclass
class SkillManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    entry_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServerManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    transport: str = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else get_runtime_paths().skills_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _skill_dir(self, name: str) -> Path:
        return self.base_dir / _slugify(name)

    def install(self, manifest: Dict[str, Any] | SkillManifest, overwrite: bool = True) -> Dict[str, Any]:
        if isinstance(manifest, SkillManifest):
            manifest = asdict(manifest)

        target_dir = self._skill_dir(manifest["name"])
        target_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = target_dir / "skill.json"
        prompt_path = target_dir / "prompt.txt"

        if manifest_path.exists() and not overwrite:
            raise FileExistsError(f"skill already exists: {manifest['name']}")

        prompt = manifest.get("entry_prompt", "")
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)
        prompt_path.write_text(prompt, encoding="utf-8")

        installed = self.get(manifest["name"])
        installed["path"] = str(target_dir)
        return installed

    def install_from_file(self, file_path: str, overwrite: bool = True) -> Dict[str, Any]:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
        return self.install(manifest, overwrite=overwrite)

    def get(self, name: str) -> Dict[str, Any]:
        target_dir = self._skill_dir(name)
        manifest_path = target_dir / "skill.json"
        if not manifest_path.exists():
            raise KeyError(name)
        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
        manifest["entry_prompt"] = (target_dir / "prompt.txt").read_text(encoding="utf-8")
        manifest["path"] = str(target_dir)
        return manifest

    def list(self) -> List[Dict[str, Any]]:
        skills = []
        for manifest_path in self.base_dir.glob("*/skill.json"):
            with manifest_path.open("r", encoding="utf-8") as file:
                manifest = json.load(file)
            manifest["path"] = str(manifest_path.parent)
            skills.append(manifest)
        skills.sort(key=lambda item: item["name"].lower())
        return skills

    def remove(self, name: str) -> bool:
        target_dir = self._skill_dir(name)
        if not target_dir.exists():
            return False
        for path in target_dir.glob("*"):
            path.unlink(missing_ok=True)
        target_dir.rmdir()
        return True


class MCPRegistry:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else get_runtime_paths().mcp_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _manifest_path(self, name: str) -> Path:
        return self.base_dir / f"{_slugify(name)}.json"

    def install(self, manifest: Dict[str, Any] | MCPServerManifest, overwrite: bool = True) -> Dict[str, Any]:
        if isinstance(manifest, MCPServerManifest):
            manifest = asdict(manifest)

        manifest_path = self._manifest_path(manifest["name"])
        if manifest_path.exists() and not overwrite:
            raise FileExistsError(f"mcp server already exists: {manifest['name']}")

        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)

        installed = self.get(manifest["name"])
        installed["path"] = str(manifest_path)
        return installed

    def install_from_file(self, file_path: str, overwrite: bool = True) -> Dict[str, Any]:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
        return self.install(manifest, overwrite=overwrite)

    def get(self, name: str) -> Dict[str, Any]:
        manifest_path = self._manifest_path(name)
        if not manifest_path.exists():
            raise KeyError(name)
        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
        manifest["path"] = str(manifest_path)
        return manifest

    def list(self) -> List[Dict[str, Any]]:
        items = []
        for manifest_path in self.base_dir.glob("*.json"):
            with manifest_path.open("r", encoding="utf-8") as file:
                manifest = json.load(file)
            manifest["path"] = str(manifest_path)
            items.append(manifest)
        items.sort(key=lambda item: item["name"].lower())
        return items

    def remove(self, name: str) -> bool:
        manifest_path = self._manifest_path(name)
        if not manifest_path.exists():
            return False
        manifest_path.unlink()
        return True


class ExtensionManager:
    def __init__(self, skill_registry: Optional[SkillRegistry] = None, mcp_registry: Optional[MCPRegistry] = None):
        self.skills = skill_registry or SkillRegistry()
        self.mcp = mcp_registry or MCPRegistry()

    def stats(self) -> Dict[str, Any]:
        return {
            "skills": len(self.skills.list()),
            "mcp_servers": len(self.mcp.list()),
        }

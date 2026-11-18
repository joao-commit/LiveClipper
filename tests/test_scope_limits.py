"""Guarda os limites desta fase: nada futuro deve existir como código fictício."""

from __future__ import annotations

import importlib
import inspect
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESERVED_PACKAGES = ("app.detection", "app.clipping", "app.publishing")
FORBIDDEN_ROUTE_TERMS = (
    "peak",
    "detect",
    "transcri",
    "clip",
    "subtitle",
    "caption",
    "buffer",
    "publish",
    "upload",
    "youtube",
    "oauth",
    "gui",
    "dashboard",
)
FORBIDDEN_RUNTIME_DEPENDENCIES = (
    "opencv",
    "ffmpeg",
    "whisper",
    "obs-websocket",
    "obsws",
    "pyqt",
    "pyside",
    "tkinter",
    "customtkinter",
    "streamlit",
    "gradio",
    "youtube",
    "google-api",
    "google-auth",
    "oauth",
)


def test_reserved_packages_have_no_executable_api() -> None:
    for package_name in RESERVED_PACKAGES:
        module = importlib.import_module(package_name)

        public_callables = [
            name
            for name, value in vars(module).items()
            if not name.startswith("_")
            and (inspect.isfunction(value) or inspect.isclass(value))
        ]

        assert public_callables == [], (
            f"{package_name} deve conter apenas documentação nesta fase; "
            f"funções fictícias encontradas: {public_callables}"
        )


def test_reserved_packages_contain_only_their_init_file() -> None:
    for package_name in RESERVED_PACKAGES:
        module = importlib.import_module(package_name)
        package_dir = Path(module.__file__).parent

        extra_modules = sorted(
            path.name for path in package_dir.glob("*.py") if path.name != "__init__.py"
        )

        assert extra_modules == [], (
            f"{package_name} deveria conter apenas __init__.py nesta fase; "
            f"módulos encontrados: {extra_modules}"
        )


def test_no_routes_for_future_phases_are_exposed(client) -> None:
    paths = client.app.openapi()["paths"]

    for path in paths:
        assert not any(term in path.lower() for term in FORBIDDEN_ROUTE_TERMS), path


def test_no_future_phase_dependencies_at_runtime() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = " ".join(project["project"]["dependencies"]).lower()

    for forbidden in FORBIDDEN_RUNTIME_DEPENDENCIES:
        assert forbidden not in dependencies, forbidden

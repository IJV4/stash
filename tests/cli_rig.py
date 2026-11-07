import io
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from builders import API_KEY
from capture_builders import a_filing_answer, a_message
from fakes.fake_providers import FakeProviders
from fakes.installed_modules import InstalledModules
from fakes.nvidia_smi import SwitchableSmi
from fakes.ocr import FakeOcr
from fakes.search_path import FakeSearchPath
from llm_rig import llm_toml

from stash.app import StashApp, build_app
from stash.capture import Filed, ProcessResult
from stash.cli import main
from stash.config import StashConfig
from stash.config.loader import load_config
from stash.domain import Item, RawCapture
from stash.evaluation import Ocr
from stash.lifecycle import Lifecycle
from stash.people import PeopleDirectory

NOON = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
LATE_EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class CliResult:
    exit_code: int
    out: str
    err: str

    def lines(self) -> list[str]:
        return self.out.splitlines()


class CliRig:
    def __init__(self, directory: Path, toml: str) -> None:
        self.directory = directory
        self.data_dir = directory / "data"
        self.config_file = directory / "stash.toml"
        self.config_file.write_text(f'data_dir = "{self.data_dir}"\n{toml}', encoding="utf-8")
        self.providers = FakeProviders()
        self.smi = SwitchableSmi()
        self.search_path = FakeSearchPath()
        self.modules = InstalledModules("yt_dlp")
        self.now = NOON
        self.ocr: Ocr = FakeOcr("")
        self.env = {"HOME": str(directory), "OPENROUTER_API_KEY": API_KEY}

    def build(self, config: StashConfig) -> StashApp:
        app = build_app(
            config,
            client=self.providers.client(),
            run=self.smi,
            which=self.search_path,
            clock=lambda: self.now,
            find_spec=self.modules,
        )
        return replace(app, ocr=self.ocr)

    def run(self, *argv: str) -> CliResult:
        return self.run_without_config(*argv, "--config", str(self.config_file))

    def run_without_config(self, *argv: str) -> CliResult:
        out, err = io.StringIO(), io.StringIO()
        exit_code = main(list(argv), factory=self.build, env=self.env, out=out, err=err)
        return CliResult(exit_code, out.getvalue(), err.getvalue())

    def received(self, text: str, message_id: str = "m1") -> RawCapture | None:
        app = self.build(load_config(self.config_file, self.env))
        try:
            return app.pipeline.receive(
                a_message(text, message_id=message_id, received_at=self.now)
            )
        finally:
            app.close()

    def filed(self, text: str, message_id: str = "m1") -> ProcessResult:
        app = self.build(load_config(self.config_file, self.env))
        try:
            return app.pipeline.handle(a_message(text, message_id=message_id, received_at=self.now))
        finally:
            app.close()

    def filed_as(self, text: str, message_id: str = "m1", **answer: object) -> Item:
        self.providers.answer = a_filing_answer(**answer)
        result = self.filed(text, message_id)
        assert isinstance(result, Filed)
        return result.item

    def through_lifecycle(self, act: Callable[[Lifecycle], object]) -> None:
        app = self.build(load_config(self.config_file, self.env))
        try:
            act(app.lifecycle)
        finally:
            app.close()

    def through_people(self, act: Callable[[PeopleDirectory], object]) -> None:
        app = self.build(load_config(self.config_file, self.env))
        try:
            act(app.people)
        finally:
            app.close()


def build_cli_rig(
    directory: Path,
    provider: str = "ollama",
    busy_fallback: str = "wait",
    filing_thinking: str | None = None,
    vision_model: str | None = None,
) -> CliRig:
    toml = llm_toml(
        provider, busy_fallback, filing_thinking=filing_thinking, vision_model=vision_model
    )
    return CliRig(directory, 'timezone = "America/Los_Angeles"\n' + toml)

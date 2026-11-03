import io
from pathlib import Path

from app_builders import an_app
from config_toml import a_toml

from stash.app import StashApp
from stash.cli import main
from stash.config import StashConfig


class Session:
    def __init__(self, directory: Path, app: StashApp | None = None) -> None:
        self.directory = directory
        self.config_file = directory / "stash.toml"
        self.config_file.write_text(a_toml(top=f'data_dir = "{directory}"'))
        self.app = an_app() if app is None else app
        self.configs: list[StashConfig] = []
        self.out = io.StringIO()
        self.err = io.StringIO()

    def factory(self, config: StashConfig) -> StashApp:
        self.configs.append(config)
        return self.app

    def run(self, *argv: str, env: dict[str, str] | None = None) -> int:
        return main(
            list(argv),
            factory=self.factory,
            env={"HOME": str(self.directory)} if env is None else env,
            out=self.out,
            err=self.err,
        )

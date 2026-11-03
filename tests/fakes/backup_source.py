from pathlib import Path

PARTIAL = b"partial"


class FakeBackupSource:
    def __init__(self, content: bytes = b"backup of the items") -> None:
        self.content = content
        self.targets: list[Path] = []
        self.fail_with: Exception | None = None

    def backup_to(self, target: Path) -> None:
        self.targets.append(target)
        if self.fail_with is not None:
            target.write_bytes(PARTIAL)
            raise self.fail_with
        target.write_bytes(self.content)

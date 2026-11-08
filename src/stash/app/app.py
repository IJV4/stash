from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from stash.app.atomic_write import write_atomically
from stash.app.library import (
    LibraryServerFactory,
    LibraryTokenMissing,
    ServingLibrary,
    library_copy_path,
)
from stash.capture import AgentCapture, BurstCoalescer, CaptureIntake, FixHandler
from stash.config import StashConfig
from stash.delivery import NudgeDelivery, ProposalDelivery
from stash.doctor import Doctor
from stash.evaluation import EvalTargets, Ocr
from stash.gpu import GpuGate
from stash.gpu_switch import GpuSwitch
from stash.library_html import RenderedLibrary, render_document
from stash.lifecycle import Lifecycle
from stash.llm import ModelRouter
from stash.people import PeopleDirectory
from stash.planning import Planning
from stash.store import BackupWriter, Closeable, Store
from stash.suggestions import SuggestionDesk


@dataclass(frozen=True, slots=True)
class StashApp:
    config: StashConfig
    store: Store
    pipeline: CaptureIntake
    agent_capture: AgentCapture
    fixes: FixHandler
    lifecycle: Lifecycle
    planning: Planning
    people: PeopleDirectory
    suggestions: SuggestionDesk
    nudge_delivery: NudgeDelivery
    proposal_delivery: ProposalDelivery
    gpu: GpuGate
    gpu_switch: GpuSwitch
    router: ModelRouter
    doctor: Doctor
    burst_factory: Callable[[], BurstCoalescer]
    clock: Callable[[], datetime]
    eval_targets: EvalTargets
    ocr: Ocr
    backups: BackupWriter
    library_servers: LibraryServerFactory
    resources: Closeable

    def local_now(self) -> datetime:
        return self.clock().astimezone(self.config.timezone)

    def today(self) -> date:
        return self.local_now().date()

    def rendered_library(self) -> RenderedLibrary:
        return render_document(self.store, self.local_now())

    def serve_only_library_page(self) -> str:
        with self.store.read_snapshot():
            return self.rendered_library().html

    def library_server(self) -> ServingLibrary:
        library = self.config.library
        if library.token is None:
            raise LibraryTokenMissing
        return self.library_servers(
            self.serve_only_library_page, library.token, library.bind, library.port
        )

    def keep_library_copy(self, data: bytes) -> None:
        write_atomically(library_copy_path(self.config.data_dir), data)

    def close(self) -> None:
        self.resources.close()

import shutil
import uuid
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from importlib.util import find_spec as importable_spec

import httpx

from stash.app.app import StashApp
from stash.app.database import open_database
from stash.app.doctor_checks import build_doctor
from stash.app.inspection import INSPECTION_DEADLINE_SECONDS, build_inspector, system_resolver
from stash.app.media_files import MEDIA_DIRECTORY, DirectoryMediaKeeper
from stash.app.ocr import make_ocr
from stash.app.providers import (
    chat_models,
    eval_chat_models,
    eval_targets,
    model_unloader,
    own_vram_usage,
    vision_models,
)
from stash.capture import (
    AgentCapture,
    BurstCoalescer,
    CapturePipeline,
    FixHandler,
    SerializedPipeline,
)
from stash.config import StashConfig
from stash.delivery import (
    AUTO_RETRY_BATCH,
    NudgeDelivery,
    PendingRetryDelivery,
    ProposalDelivery,
)
from stash.enrich.html_meta import Resolver
from stash.enrich.ytdlp import default_ytdlp_extract
from stash.filing import Filer
from stash.gpu import GpuGate
from stash.gpu.probe import CommandRunner, NvidiaSmiProbe, run_command
from stash.gpu_switch import GpuSwitch
from stash.http_client import make_http_client
from stash.lifecycle import Lifecycle
from stash.llm import ModelRouter
from stash.nudges import DigestBuilder, Nudger, PersonDates, Schedule
from stash.people import PeopleDirectory, PeopleLinker
from stash.planning import Declines, Planning, StepProposer
from stash.store.backup import Backups
from stash.suggestions import QuietPicks, SuggestionDesk, SuggestionEngine


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex


def build_app(
    config: StashConfig,
    *,
    client: httpx.Client | None = None,
    run: CommandRunner = run_command,
    which: Callable[[str], str | None] = shutil.which,
    clock: Callable[[], datetime] = _utc_now,
    extract: Callable[[str], Mapping[str, object]] = default_ytdlp_extract,
    inspection_deadline_seconds: float = INSPECTION_DEADLINE_SECONDS,
    resolve: Resolver = system_resolver,
    find_spec: Callable[[str], object | None] = importable_spec,
) -> StashApp:
    resources = ExitStack()
    try:
        http = resources.enter_context(make_http_client()) if client is None else client
        sqlite = open_database(config, resources)
        gpu_probe = NvidiaSmiProbe(run)
        gate = GpuGate(gpu_probe, own_vram_usage(config.llm, http), sqlite, config.gpu)
        models = chat_models(config.llm, http)
        router = ModelRouter(config.llm, models, gate)
        people = PeopleDirectory(sqlite, _new_id, clock)
        pipeline = SerializedPipeline(
            CapturePipeline(
                sqlite,
                build_inspector(http, extract, resolve, inspection_deadline_seconds),
                Filer(router, clock, config.timezone),
                _new_id,
                clock,
                PeopleLinker(people, sqlite),
                DirectoryMediaKeeper(config.data_dir / MEDIA_DIRECTORY),
            )
        )
        lifecycle = Lifecycle(sqlite, _new_id, clock, config.timezone)
        planning = Planning(
            sqlite,
            StepProposer(router, clock, config.timezone),
            Declines(sqlite),
            _new_id,
            clock,
            config.timezone,
        )
        suggestions = SuggestionDesk(sqlite, SuggestionEngine(router, clock, config.timezone))
        schedule = Schedule(config.nudges, config.timezone)
        person_dates = PersonDates(sqlite, schedule, config.people.lead_days)
        digests = DigestBuilder(sqlite, QuietPicks(suggestions), schedule)
        return StashApp(
            config=config,
            store=sqlite,
            pipeline=pipeline,
            agent_capture=AgentCapture(pipeline, _new_id, clock),
            fixes=FixHandler(sqlite, lifecycle, planning, clock, config.timezone),
            lifecycle=lifecycle,
            planning=planning,
            people=people,
            suggestions=suggestions,
            nudge_delivery=NudgeDelivery(Nudger(sqlite, schedule, person_dates), digests),
            proposal_delivery=ProposalDelivery(planning, sqlite),
            retry_delivery=PendingRetryDelivery(
                pipeline,
                gate.is_busy,
                sqlite,
                timedelta(minutes=config.nudges.auto_retry_minutes),
                AUTO_RETRY_BATCH,
            ),
            gpu=gate,
            gpu_switch=GpuSwitch(gate, model_unloader(config.llm, http)),
            router=router,
            doctor=build_doctor(config, sqlite, http, gpu_probe, which, find_spec, clock),
            burst_factory=lambda: BurstCoalescer(config.burst_window_seconds),
            clock=clock,
            eval_targets=eval_targets(
                config.llm, eval_chat_models(config.llm, http), vision_models(config.llm, http)
            ),
            ocr=make_ocr(which),
            backups=Backups(sqlite, sqlite, clock),
            resources=resources,
        )
    except BaseException:
        resources.close()
        raise

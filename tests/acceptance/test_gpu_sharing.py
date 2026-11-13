from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from builders import BASE, PLUS_FIVE
from capture_builders import a_filing_answer, a_message
from capture_narrowing import handle_deferred, handle_filed
from capture_rig import build_rig as build_capture_rig
from gate_rig import CONFIG, a_gate
from llm_rig import (
    BUSY_GPU,
    FREE_GPU,
    HOT_GPU,
    OLLAMA_ROOT,
    OLLAMA_URL,
    OPENROUTER_URL,
    ask,
    build_rig,
    llm_toml,
    missing_nvidia_smi,
)

from stash.capture import DeferralReason
from stash.config import LlmTask
from stash.gpu.gate import NO_GPU_READING
from stash.llm import LlmDeferred


def test_a_busy_gpu_defers_ollama_work_without_sending_a_request(tmp_path: Path) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), BUSY_GPU)

    # Execute
    with pytest.raises(LlmDeferred):
        ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    assert rig.requests == []


def test_a_busy_gpu_sends_work_to_openrouter_when_the_fallback_is_openrouter(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama", busy_fallback="openrouter"), BUSY_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    assert rig.urls() == [OPENROUTER_URL]


def test_turning_the_gpu_off_defers_work_until_the_switch_expires(tmp_path: Path) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)
    rig.gate.turn_off(BASE)
    before_expiry = BASE + timedelta(hours=3, minutes=59)
    after_expiry = BASE + timedelta(hours=4, minutes=1)

    # Execute
    with pytest.raises(LlmDeferred):
        ask(rig.router.model_for(LlmTask.FILING, before_expiry))
    ask(rig.router.model_for(LlmTask.FILING, after_expiry))

    # Assert
    assert rig.urls() == [OLLAMA_URL]


def test_turning_the_gpu_back_on_lets_work_flow_before_the_switch_expires(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)
    rig.gate.turn_off(BASE)
    rig.gate.turn_on()

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE + timedelta(hours=1)))

    # Assert
    assert rig.urls() == [OLLAMA_URL]


def test_another_application_filling_the_vram_makes_the_gate_busy(tmp_path: Path) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), BUSY_GPU)

    # Execute
    status = rig.gate.status(BASE)

    # Assert
    assert (status.busy, status.reason) == (True, "other apps use 20000 MiB")


def test_vram_held_by_stashs_own_ollama_model_is_not_counted_against_the_gpu(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), BUSY_GPU, own_mib=19000)

    # Execute
    status = rig.gate.status(BASE)

    # Assert
    assert (status.busy, status.reason) == (False, "GPU is free")


def test_foreign_utilisation_above_the_limit_with_no_stash_model_loaded_makes_the_gate_busy(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), HOT_GPU)

    # Execute
    status = rig.gate.status(BASE)

    # Assert
    assert (status.busy, status.reason) == (True, "GPU 95% busy")


def test_a_missing_nvidia_smi_makes_the_gate_busy_by_default(tmp_path: Path) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), None, run=missing_nvidia_smi())

    # Execute
    status = rig.gate.status(BASE)

    # Assert
    assert (status.busy, status.reason) == (True, NO_GPU_READING)


def test_a_missing_nvidia_smi_leaves_the_gate_free_when_the_config_says_so(tmp_path: Path) -> None:
    # Setup
    toml = llm_toml("ollama") + '[gpu]\nwhen_unreadable = "free"\n'
    rig = build_rig(tmp_path, toml, None, run=missing_nvidia_smi())

    # Execute
    status = rig.gate.status(BASE)

    # Assert
    assert (status.busy, status.reason) == (False, "no GPU info")


def test_a_capture_is_deferred_and_stays_pending_while_the_gpu_cannot_be_read() -> None:
    # Setup
    rig = build_capture_rig(answer=a_filing_answer(), gate=a_gate(None))

    # Execute
    result = handle_deferred(rig, a_message("Ramen in Shibuya"))

    # Assert
    assert result.reason == DeferralReason.GPU_BUSY
    assert len(rig.store.pending_captures()) == 1


def test_a_capture_is_filed_when_the_gpu_cannot_be_read_and_the_config_says_free() -> None:
    # Setup
    free_when_unreadable = replace(CONFIG, when_unreadable="free")
    rig = build_capture_rig(
        answer=a_filing_answer(), gate=a_gate(None, config=free_when_unreadable)
    )

    # Execute
    result = handle_filed(rig, a_message("Ramen in Shibuya"))

    # Assert
    assert rig.store.pending_captures() == []
    assert result.item.id in {item.id for item in rig.store.list_items()}


def test_work_configured_for_openrouter_is_never_deferred_while_the_gpu_is_busy(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("openrouter"), BUSY_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    assert rig.urls() == [OPENROUTER_URL]


def test_the_status_reads_turned_off_until_the_expiry_in_the_callers_timezone(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)
    now = BASE.astimezone(PLUS_FIVE)
    rig.gate.turn_off(now)

    # Execute
    status = rig.gate.status(now)

    # Assert
    assert status.reason == "turned off until 21:00"


def test_the_switch_off_survives_a_restart(tmp_path: Path) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)
    rig.gate.turn_off(BASE)

    # Execute
    restarted = rig.restarted_gate()

    # Assert
    assert restarted.is_busy(BASE + timedelta(hours=1))


def test_telling_ollama_to_unload_posts_keep_alive_zero_for_the_configured_model(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)

    # Execute
    rig.ollama_control().unload()

    # Assert
    request = rig.requests[0]
    assert (request.method, str(request.url), rig.sent_json()) == (
        "POST",
        f"{OLLAMA_ROOT}/api/generate",
        {"model": "local-model", "keep_alive": 0},
    )

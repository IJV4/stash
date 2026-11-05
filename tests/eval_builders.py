from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fakes.chat_model import FakeChatModel
from fakes.fake_providers import FILING_ANSWER

from stash.config import ModelChoice, ProviderName, Thinking
from stash.domain import ItemType, Route, Stage
from stash.evaluation import (
    CaseKind,
    CaseResult,
    EvalArm,
    EvalCase,
    EvalField,
    EvalTarget,
    EvalTargets,
    Expectation,
    FieldMismatch,
    NamedModel,
)
from stash.llm import ChatModel

LONG_MULTILINE_VALUE = ("line one of the model output\n" * 70)[:2048]
LOCAL_MODEL_NAME = "local"
LOCAL_VISION_MODEL_NAME = "local-vision"


def an_expectation(**overrides: Any) -> Expectation:
    fields: dict[str, Any] = {"route": Route.CAPTURE}
    return Expectation(**{**fields, **overrides})


def a_text_case(**overrides: Any) -> EvalCase:
    fields: dict[str, Any] = {
        "id": "t01",
        "kind": CaseKind.TEXT,
        "text": "Ramen Ichiban in Shibuya, Tokyo",
        "link": None,
        "image_path": None,
        "expect": an_expectation(item_type=ItemType.PLACE, stage=Stage.WANT_TO),
    }
    return EvalCase(**{**fields, **overrides})


def an_image_case(**overrides: Any) -> EvalCase:
    fields: dict[str, Any] = {
        "id": "i01",
        "kind": CaseKind.IMAGE,
        "text": "save this",
        "link": None,
        "image_path": Path("images/recipe_card.png"),
        "expect": an_expectation(item_type=ItemType.RECIPE),
    }
    return EvalCase(**{**fields, **overrides})


def a_mismatch(
    field: EvalField = EvalField.STAGE, expected: str = "planned", got: str = "want_to"
) -> FieldMismatch:
    return FieldMismatch(field, expected, got)


def a_result(**overrides: Any) -> CaseResult:
    fields: dict[str, Any] = {
        "case_id": "t01",
        "arm": EvalArm.TEXT,
        "passed_fields": frozenset({EvalField.ROUTE}),
        "failed_fields": frozenset(),
        "latency_s": 1.0,
        "error": None,
    }
    fields.update(overrides)
    if "mismatches" not in overrides and fields["error"] is None:
        fields["mismatches"] = tuple(
            a_mismatch(field) for field in EvalField if field in fields["failed_fields"]
        )
    return CaseResult(**fields)


def a_named_model(name: str = LOCAL_MODEL_NAME, chat: ChatModel | None = None) -> NamedModel:
    return NamedModel(name, FakeChatModel() if chat is None else chat)


def a_named_vision_model(chat: ChatModel | None = None) -> NamedModel:
    return a_named_model(LOCAL_VISION_MODEL_NAME, chat)


def a_target(
    provider: ProviderName = ProviderName.OLLAMA,
    thinking: Thinking = Thinking.DEFAULT,
    text: NamedModel | None = None,
    vision: NamedModel | None = None,
) -> EvalTarget:
    return EvalTarget(
        ModelChoice(provider, thinking), a_named_model() if text is None else text, vision
    )


def an_eval_targets(
    *providers: ProviderName,
    configured: Thinking = Thinking.DEFAULT,
    model_names: Mapping[ProviderName, str] | None = None,
    model: ChatModel | None = None,
) -> EvalTargets:
    names = model_names or {}
    return EvalTargets(
        tuple(
            a_target(
                provider,
                thinking,
                text=a_named_model(
                    names.get(provider, LOCAL_MODEL_NAME),
                    FakeChatModel(FILING_ANSWER) if model is None else model,
                ),
            )
            for provider in providers or (ProviderName.OLLAMA,)
            for thinking in Thinking
        ),
        configured,
    )


def target_for(targets: EvalTargets, provider: ProviderName, thinking: Thinking) -> EvalTarget:
    return targets.select((provider.value,), (thinking,))[0]


def arm_headings(report: str) -> list[str]:
    return [line for line in report.splitlines() if " arm (" in line]

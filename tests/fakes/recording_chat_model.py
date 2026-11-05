from typing import Protocol

from stash.llm import ChatMessage, ChatModel


class RecordingChatModel(ChatModel, Protocol):
    calls: list[list[ChatMessage]]

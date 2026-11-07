from stash.hermes_adapter.plugin import AdapterState, SharedApp
from stash.hermes_adapter.telegram_link import TelegramLink
from stash.hermes_adapter.ticker import TickerLauncher


def an_adapter_state() -> AdapterState:
    return AdapterState(SharedApp(), TelegramLink(), TickerLauncher())

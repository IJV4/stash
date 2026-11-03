class CloseCounter:
    def __init__(self) -> None:
        self.closes = 0

    def close(self) -> None:
        self.closes += 1

from typing_extensions import Protocol


class PConverter(Protocol):
    def convert(self, raw_html: str) -> str:
        pass

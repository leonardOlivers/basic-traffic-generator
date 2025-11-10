thonimport asyncio
from typing import Iterable, List

def load_urls_from_file(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls

class URLQueue:
    def __init__(self, urls: Iterable[str]) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        for url in urls:
            self._queue.put_nowait(url)

    def get_nowait(self) -> str:
        return self._queue.get_nowait()

    def task_done(self) -> None:
        self._queue.task_done()

    def empty(self) -> bool:
        return self._queue.empty()
"""Lange Arbeiten als Ereignisstrom (Schnitt RAD-17, Werbestellen RAD-32): start, progress (Schritt, Gesamt, Text),
done mit dem Ergebnis oder error mit der Meldung. Jeder Fehler landet im Strom, sonst wartete die Oberfläche."""
import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.responses import StreamingResponse

Fortschritt = Callable[[int, int, str], None]


def ereignisstrom(arbeit: Callable[[Fortschritt], Awaitable[Any]], ergebnis: str = "count") -> StreamingResponse:
    """`arbeit(fortschritt)` im Hintergrund; das Ergebnis steht im Ende-Ereignis unter `ergebnis`."""
    queue: asyncio.Queue = asyncio.Queue()

    def fortschritt(schritt: int, gesamt: int, text: str) -> None:
        queue.put_nowait({"type": "progress", "step": schritt, "total": gesamt, "message": text})

    async def laufen():
        try:
            queue.put_nowait({"type": "done", ergebnis: await arbeit(fortschritt)})
        except Exception as f:  # noqa: BLE001 - jeder Fehler gehört in den Strom
            queue.put_nowait({"type": "error", "message": str(f)})

    async def strom():
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        aufgabe = asyncio.create_task(laufen())
        while True:
            evt = await queue.get()
            yield f"data: {json.dumps(evt)}\n\n"
            if evt["type"] in ("done", "error"):
                break
        await aufgabe

    return StreamingResponse(strom(), media_type="text/event-stream")

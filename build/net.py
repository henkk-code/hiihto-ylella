"""Pieni HTTP-apuri: uudelleenyritykset ja selkeä User-Agent."""
import time
import urllib.request

USER_AGENT = "hiihto-ylella/1.0 (+https://github.com/henkk-code/hiihto-ylella)"


def fetch(url: str, timeout: int = 30, retries: int = 3, backoff: float = 2.0) -> bytes:
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 – kaikki verkkovirheet käsitellään samoin
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Haku epäonnistui: {url}: {last_error}")

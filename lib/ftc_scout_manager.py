"""
Manages interaction with the FTC Scout REST API (api.ftcscout.org/rest/v1).

Provides helpers to:
  - Search / list FTC events for a season.
  - Fetch all team event participations for a specific event.

Results are cached to <project_root>/data/ so the app can work offline after
the first successful fetch.
"""

import json
import requests
from pathlib import Path

BASE_URL = "https://api.ftcscout.org/rest/v1"

_MODULE_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _MODULE_DIR.parent
DATA_DIR = _ROOT_DIR / "data"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class FTCScoutManager:
    """Fetch and cache FTC Scout API data."""

    def __init__(self) -> None:
        self.events_cache: dict[int, list] = {}
        self.teams_cache: dict[str, list] = {}
        # Flat number → name mapping populated whenever teams are cached
        self._team_names: dict[int, str] = {}

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict | None = None):
        """Make a GET request; return parsed JSON or None on failure."""
        url = BASE_URL + endpoint
        try:
            # (connect_timeout_s, read_timeout_s)
            resp = requests.get(url, params=params or {}, timeout=(10, 30))
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as exc:
            print(f"[FTCScout] HTTP error {exc.response.status_code}: {exc}")
        except requests.exceptions.RequestException as exc:
            print(f"[FTCScout] Request error: {exc}")
        return None

    # ── Events ───────────────────────────────────────────────────────────────

    def search_events(
        self,
        season: int,
        *,
        region: str | None = None,
        event_type: str | None = None,
        has_matches: bool | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
        search_text: str | None = None,
        force_refresh: bool = False,
    ) -> list | None:
        """Search for FTC events.

        Calls ``GET /events/search/:season`` with optional query parameters.

        Args:
            season: FTC season year (e.g. 2025 for 2025-26 season).
            region: RegionOption filter.
            event_type: EventType filter.
            has_matches: Boolean filter.
            start: ISO date string (YYYY-MM-DD).
            end: ISO date string (YYYY-MM-DD).
            limit: Maximum number of results.
            search_text: Free-text event name search.
            force_refresh: Bypass disk cache and always hit the API.

        Returns:
            List of event dicts or None on failure.
        """
        season = int(season)

        cache_key = season
        if not force_refresh:
            cached = self.events_cache.get(cache_key)
            if cached is not None:
                return cached
            saved = self._load_events_from_file(season)
            if saved is not None:
                self.events_cache[cache_key] = saved
                return saved

        params: dict = {}
        if region is not None:
            params["region"] = region
        if event_type is not None:
            params["type"] = event_type
        if has_matches is not None:
            params["hasMatches"] = str(has_matches).lower()
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        if limit is not None:
            params["limit"] = limit
        if search_text:
            params["searchText"] = search_text

        data = self._get(f"/events/search/{season}", params)
        if data is not None:
            self.events_cache[cache_key] = data
            self._save_events_to_file(season, data)
        return data

    def _save_events_to_file(self, season: int, data: list) -> bool:
        _ensure_data_dir()
        path = DATA_DIR / f"ftc_events_{season}.json"
        try:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return True
        except OSError as exc:
            print(f"[FTCScout] Cannot save events: {exc}")
            return False

    def _load_events_from_file(self, season: int) -> list | None:
        path = DATA_DIR / f"ftc_events_{season}.json"
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[FTCScout] Cannot load events cache: {exc}")
            return None

    # ── Teams for event ──────────────────────────────────────────────────────

    def get_teams_for_event(
        self,
        season: int,
        event_code: str,
        *,
        force_refresh: bool = False,
    ) -> list | None:
        """Fetch all team event participations for an event.

        Calls ``GET /events/:season/:code/teams``.

        Args:
            season: FTC season year.
            event_code: Event short code (e.g. "TXHOU").
            force_refresh: Bypass disk cache.

        Returns:
            List of participation dicts or None on failure.
        """
        season = int(season)
        cache_key = f"{season}_{event_code}"

        if not force_refresh:
            cached = self.teams_cache.get(cache_key)
            if cached is not None:
                return cached
            saved = self._load_teams_from_file(cache_key)
            if saved is not None:
                self.teams_cache[cache_key] = saved
                self._index_team_names(saved)
                return saved

        data = self._get(f"/events/{season}/{event_code}/teams")
        if data is not None:
            self.teams_cache[cache_key] = data
            self._index_team_names(data)
            self._save_teams_to_file(cache_key, data)
        return data

    def _save_teams_to_file(self, key: str, data: list) -> bool:
        _ensure_data_dir()
        path = DATA_DIR / f"ftc_teams_{key}.json"
        try:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return True
        except OSError as exc:
            print(f"[FTCScout] Cannot save teams: {exc}")
            return False

    def _load_teams_from_file(self, key: str) -> list | None:
        path = DATA_DIR / f"ftc_teams_{key}.json"
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[FTCScout] Cannot load teams cache: {exc}")
            return None

    # ── Nickname helpers ─────────────────────────────────────────────────────

    def _index_team_names(self, participations: list) -> None:
        """Populate ``_team_names`` dict from a list of participation entries."""
        for entry in participations or []:
            t = entry.get("team") or {}
            num = t.get("number") or entry.get("teamNumber")
            if num is None:
                continue
            name = t.get("name") or entry.get("teamName") or ""
            if name:
                try:
                    self._team_names[int(num)] = name
                except (TypeError, ValueError):
                    pass

    def get_team_nickname(self, team_number) -> str:
        """Return cached team name (O(1) lookup), or the number as a string."""
        try:
            return self._team_names.get(int(team_number), str(team_number))
        except (TypeError, ValueError):
            return str(team_number)

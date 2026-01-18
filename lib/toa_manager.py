"""\
Manages interaction with The Orange Alliance (TOA) API for FTC.

This module provides a class to fetch event and team data from TOA,
and to manage a local cache of team names to avoid excessive API calls.

Offline cache files are stored next to this module:
- `toa_events_<season_key>.json`
- `teams_<event_key>.json`
- `toa_team_events_<team_number>_<season_key>.json`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from json import JSONDecodeError
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://theorangealliance.org/api"
DATA_DIR = Path(__file__).resolve().parent
DEFAULT_APPLICATION_ORIGIN = "Overture_Analizador_FTC"

# Module-level persistent team names cache for Raspberry Pi optimization
# This survives TOAManager instance recreation and reduces file I/O
_persistent_team_names: dict[int, str] = {}
_team_names_loaded_from_file: bool = False


def _ensure_data_dir() -> None:
    """Make sure the cache directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_persistent_team_names() -> None:
    """Load team names from all cached team files once at module level."""
    global _persistent_team_names, _team_names_loaded_from_file
    
    if _team_names_loaded_from_file:
        return
    
    _team_names_loaded_from_file = True
    
    # Scan for all teams_*.json files and preload names
    try:
        for team_file in DATA_DIR.glob("teams_*.json"):
            try:
                with team_file.open("r", encoding="utf-8") as f:
                    teams_data = json.load(f)
                    for team in teams_data or []:
                        if not isinstance(team, dict):
                            continue
                        number = team.get("team_number")
                        if number is None:
                            continue
                        nickname = team.get("team_name_short") or team.get("nickname") or team.get("name")
                        if nickname:
                            try:
                                _persistent_team_names[int(number)] = str(nickname)
                            except (TypeError, ValueError):
                                pass
            except (json.JSONDecodeError, OSError):
                continue
    except Exception:
        pass  # Silently fail - caching is best-effort


class TOAManager:
    """A manager for fetching and caching data from The Orange Alliance API."""

    def __init__(
        self,
        api_key: str | None = None,
        application_origin: str | None = None,
        application_id: str | None = None,
        use_api: bool = True,
    ) -> None:
        self.api_key = api_key
        # Backward/alternate naming support:
        # - older code used `application_id`
        # - current TOA header requires `X-Application-Origin`
        self.application_origin = application_origin or application_id or DEFAULT_APPLICATION_ORIGIN
        self.use_api = bool(use_api)

        if self.use_api:
            if not self.api_key:
                raise ValueError("TOA API Key is required when API access is enabled.")
            self.headers = {
                # Required by TOA
                "X-TOA-Key": self.api_key,
                "X-Application-Origin": self.application_origin,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        else:
            self.headers = {}

        # Load persistent cache on first access
        _load_persistent_team_names()
        
        # Instance-level cache inherits from persistent cache
        self.team_names: dict[Any, str] = dict(_persistent_team_names)
        self.events_cache: dict[int, list[dict[str, Any]]] = {}
        self.team_events_cache: dict[tuple[int, int], list[dict[str, Any]]] = {}
        self.team_cache: dict[str, list[dict[str, Any]]] = {}
        self.last_error: dict[str, Any] | None = None

        # Use a session with retries to survive flaky Wi‑Fi / interrupted transfers.
        self._session: requests.Session | None = None
        if self.use_api:
            session = requests.Session()
            retry = Retry(
                total=3,
                connect=3,
                read=3,
                status=3,
                backoff_factor=0.6,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            self._session = session

    def set_api_usage(self, enabled: bool) -> None:
        """Toggle whether API requests are allowed."""
        enabled = bool(enabled)
        if enabled:
            if not self.api_key:
                raise ValueError("No API key configured; cannot enable API access.")
            self.headers = {
                "X-TOA-Key": self.api_key,
                "X-Application-Origin": self.application_origin or DEFAULT_APPLICATION_ORIGIN,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        else:
            self.headers = {}
        self.use_api = enabled

    def _get_toa_data(self, endpoint: str, params: dict[str, Any] | None = None):
        """Generic function to make a GET request to the TOA API."""
        if not self.use_api:
            print("[INFO] API access disabled. Using cached data only.")
            self.last_error = {
                "type": "offline",
                "message": "API access disabled (offline mode).",
            }
            return None

        url = BASE_URL.rstrip("/") + endpoint
        requester = self._session if self._session is not None else requests
        last_exc: Exception | None = None

        # Manual retries because "IncompleteRead" often happens mid-response (after headers)
        # and may not be retried by urllib3's status-based retry.
        for attempt in range(1, 4):
            try:
                # (connect timeout, read timeout)
                response = requester.get(url, headers=self.headers, params=params, timeout=(10, 60))

                # Try to parse JSON even for non-2xx so we can show TOA's message.
                try:
                    data = response.json()
                except JSONDecodeError:
                    content_type = response.headers.get("content-type", "")
                    body_preview = (response.text or "")[:250].replace("\n", " ")
                    self.last_error = {
                        "type": "non_json",
                        "status": response.status_code,
                        "content_type": content_type,
                        "url": url,
                        "preview": body_preview,
                        "attempt": attempt,
                    }
                    print(
                        "[ERROR] TOA API response was not valid JSON. "
                        f"status={response.status_code} content-type={content_type!r} url={url!r} "
                        f"preview={body_preview!r}"
                    )
                    return None

                if response.status_code >= 400:
                    toa_message = None
                    if isinstance(data, dict):
                        toa_message = data.get("_message") or data.get("message")
                    self.last_error = {
                        "type": "http",
                        "status": response.status_code,
                        "url": url,
                        "message": toa_message,
                        "attempt": attempt,
                    }
                    print(
                        "[ERROR] TOA API request failed. "
                        f"status={response.status_code} url={url!r} message={toa_message!r}"
                    )
                    return None

                self.last_error = None
                # Some TOA endpoints wrap results; accept both styles.
                if isinstance(data, dict) and "data" in data:
                    return data.get("data")
                return data
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError) as e:
                last_exc = e
                self.last_error = {
                    "type": "request_exception",
                    "url": url,
                    "message": str(e),
                    "attempt": attempt,
                }
                print(f"[WARN] TOA transfer interrupted (attempt {attempt}/3): {e}")
                time.sleep(0.8 * attempt)
                continue
            except requests.exceptions.RequestException as e:
                last_exc = e
                self.last_error = {
                    "type": "request_exception",
                    "url": url,
                    "message": str(e),
                    "attempt": attempt,
                }
                print(f"[WARN] TOA request failed (attempt {attempt}/3): {e}")
                time.sleep(0.8 * attempt)
                continue

        if last_exc is not None:
            print(f"[ERROR] TOA request failed after retries: {last_exc}")
        return None

    def get_events_by_season(self, season_key: int | str, force_refresh: bool = False):
        """Fetch a simplified list of all FTC events for a given TOA season_key (e.g., 2425)."""
        try:
            season_key_int = int(str(season_key).strip())
        except (TypeError, ValueError):
            season_key_int = None
        if season_key_int is None:
            return None

        if not force_refresh:
            cached = self.events_cache.get(season_key_int)
            if cached:
                return cached

            saved = self.load_events_from_file(season_key_int)
            if saved is not None:
                self.events_cache[season_key_int] = saved
                return saved

        if not self.use_api:
            print(f"[INFO] Offline mode: no cached events found for season {season_key_int}.")
            return None

        print(f"Fetching events for season {season_key_int}...")
        # TOA: /event?season_key={season_key}
        events = self._get_toa_data("/event", params={"season_key": season_key_int})
        normalized = self._normalize_events(events)
        if normalized is not None:
            self.events_cache[season_key_int] = normalized
            self.save_events_to_file(season_key_int, normalized)
        return normalized

    def get_events_for_team_in_season(self, team_number: int | str, season_key: int | str, force_refresh: bool = False):
        """Fetch events where a specific team participated in a season.

        TOA endpoint: `/team/{teamKey}/events/{seasonKey}`
        Returns normalized list of `{key, name}`.
        """
        try:
            team_int = int(str(team_number).strip())
            season_int = int(str(season_key).strip())
        except (TypeError, ValueError):
            return None

        cache_key = (team_int, season_int)
        if not force_refresh:
            cached = self.team_events_cache.get(cache_key)
            if cached:
                return cached

            saved = self.load_team_events_from_file(team_int, season_int)
            if saved is not None:
                self.team_events_cache[cache_key] = saved
                return saved

        if not self.use_api:
            print(f"[INFO] Offline mode: no cached team events found for team {team_int} season {season_int}.")
            return None

        print(f"Fetching events for team {team_int} season {season_int}...")
        events = self._get_toa_data(f"/team/{team_int}/events/{season_int}")
        normalized = self._normalize_team_events(events)
        if normalized is not None:
            self.team_events_cache[cache_key] = normalized
            self.save_team_events_to_file(team_int, season_int, normalized)
        return normalized

    # Backwards-compatible alias used by older UI code.
    def get_events_for_year(self, year: int, force_refresh: bool = False):
        return self.get_events_by_season(year, force_refresh=force_refresh)

    def _normalize_events(self, events):
        if events is None:
            return None
        if not isinstance(events, list):
            return None

        normalized: list[dict[str, Any]] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue

            key = ev.get("key") or ev.get("event_key") or ev.get("eventKey") or ev.get("event_code")
            name = ev.get("event_name") or ev.get("name") or ev.get("eventName") or key
            if not key:
                continue
            normalized.append({"key": str(key), "name": str(name) if name is not None else str(key)})

        return normalized

    def _normalize_team_events(self, events):
        """Normalize `/team/{team}/events/{season}` payload to `{key, name}`."""
        if events is None:
            return None
        if not isinstance(events, list):
            return None

        normalized: list[dict[str, Any]] = []
        for item in events:
            if not isinstance(item, dict):
                continue

            event_key = item.get("event_key") or item.get("eventKey") or item.get("key")
            event_obj = item.get("event") if isinstance(item.get("event"), dict) else None
            event_name = None
            if event_obj:
                event_name = event_obj.get("event_name") or event_obj.get("name")
                if not event_key:
                    event_key = event_obj.get("event_key") or event_obj.get("key")

            # Some API shapes may just be an event object already.
            if not event_key and any(k in item for k in ("event_name", "name")):
                event_key = item.get("event_key") or item.get("key")
                event_name = item.get("event_name") or item.get("name")

            if not event_key:
                continue
            normalized.append({"key": str(event_key), "name": str(event_name) if event_name else str(event_key)})

        return normalized

    def get_teams_for_event(self, event_key: str, force_refresh: bool = False):
        """Fetch a list of all teams for a given FTC event."""
        event_key = str(event_key).strip()
        if not event_key:
            return None

        if not force_refresh:
            cached = self.team_cache.get(event_key)
            if cached is not None:
                return cached

            saved = self.load_teams_from_file(event_key)
            if saved is not None:
                self.team_cache[event_key] = saved
                return saved

        if not self.use_api:
            print(f"[INFO] Offline mode: no cached team data found for {event_key}.")
            return None

        print(f"Fetching teams for event {event_key}...")
        teams = self._get_toa_data(f"/event/{event_key}/teams")
        normalized = self._normalize_teams(teams)
        if normalized is not None:
            self.team_cache[event_key] = normalized
            self._update_team_names(normalized)
            self.save_teams_to_file(event_key, normalized)
        return normalized

    def _normalize_teams(self, teams):
        if teams is None:
            return None
        if not isinstance(teams, list):
            return None

        normalized: list[dict[str, Any]] = []
        for team in teams:
            if not isinstance(team, dict):
                continue

            number = (
                team.get("team_number")
                or team.get("teamNumber")
                or team.get("number")
                or team.get("team")
                or team.get("team_num")
            )
            if number is None:
                continue

            short_name = team.get("team_name_short") or team.get("teamNameShort") or team.get("name_short")
            nickname = short_name or team.get("nickname") or team.get("name") or team.get("team_name") or f"Team {number}"
            normalized.append(
                {
                    "team_number": number,
                    "team_name_short": short_name,
                    "nickname": nickname,
                    "name": team.get("name") or nickname,
                }
            )

        return normalized

    def save_events_to_file(self, year_or_season: int, events_data) -> bool:
        if events_data is None:
            return False

        _ensure_data_dir()
        filename = DATA_DIR / f"toa_events_{int(year_or_season)}.json"
        try:
            with filename.open("w", encoding="utf-8") as f:
                json.dump(events_data, f, indent=4)
            print(f"Successfully saved events to {filename}")
            return True
        except IOError as e:
            print(f"Error saving events to file: {e}")
            return False

    def load_events_from_file(self, year_or_season: int):
        candidate_filenames = [
            DATA_DIR / f"toa_events_{int(year_or_season)}.json",
            # Back-compat with older cache names.
            DATA_DIR / f"events_{int(year_or_season)}.json",
        ]
        target_file = next((path for path in candidate_filenames if path.exists()), None)
        if not target_file:
            return None

        try:
            with target_file.open("r", encoding="utf-8") as f:
                events = json.load(f)
            return self._normalize_events(events) or []
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading events from {target_file}: {e}")
            return None

    def save_team_events_to_file(self, team_number: int, season_key: int, events_data) -> bool:
        if events_data is None:
            return False

        _ensure_data_dir()
        filename = DATA_DIR / f"toa_team_events_{int(team_number)}_{int(season_key)}.json"
        try:
            with filename.open("w", encoding="utf-8") as f:
                json.dump(events_data, f, indent=4)
            print(f"Successfully saved team events to {filename}")
            return True
        except IOError as e:
            print(f"Error saving team events to file: {e}")
            return False

    def load_team_events_from_file(self, team_number: int, season_key: int):
        candidate_filenames = [
            DATA_DIR / f"toa_team_events_{int(team_number)}_{int(season_key)}.json",
        ]
        target_file = next((path for path in candidate_filenames if path.exists()), None)
        if not target_file:
            return None

        try:
            with target_file.open("r", encoding="utf-8") as f:
                events = json.load(f)
            return self._normalize_events(events) or []
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading team events from {target_file}: {e}")
            return None

    def save_teams_to_file(self, event_key: str, teams_data) -> bool:
        if teams_data is None:
            return False

        _ensure_data_dir()
        # Keep compatibility with the existing offline format.
        filename = DATA_DIR / f"teams_{event_key}.json"
        try:
            with filename.open("w", encoding="utf-8") as f:
                json.dump(teams_data, f, indent=4)
            print(f"Successfully saved team data to {filename}")
            self.team_cache[event_key] = teams_data
            self._update_team_names(teams_data)
            return True
        except IOError as e:
            print(f"Error saving team data to file: {e}")
            return False

    def load_teams_from_file(self, event_key: str):
        candidate_filenames = [
            # Back-compat with older cache names.
            DATA_DIR / f"teams_{event_key}.json",
            DATA_DIR / f"tba_teams_{event_key}.json",
        ]

        target_file = next((path for path in candidate_filenames if path.exists()), None)
        if not target_file:
            return None

        try:
            with target_file.open("r", encoding="utf-8") as f:
                teams_data = json.load(f)

            if not teams_data:
                print(f"No team entries found in {target_file}.")
                return None

            normalized = self._normalize_teams(teams_data)
            if not normalized:
                return None

            self.team_cache[event_key] = normalized
            self._update_team_names(normalized)
            print(f"Successfully loaded {len(normalized)} teams from {target_file.name}")
            return normalized
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing team data from {target_file}: {e}")
            return None

    def get_team_name(self, team_number):
        """Get a team's short name from cache (or fetch it if API is enabled)."""
        global _persistent_team_names
        # FTC team numbers can be 1-5 digits; keep as int for stable cache keys.
        try:
            team_key = int(str(team_number).strip())
        except (TypeError, ValueError):
            team_key = None

        if team_key is not None and team_key in self.team_names:
            return self.team_names[team_key]

        # Fallback: also check string form in case cache was populated differently
        if str(team_number) in self.team_names:
            return self.team_names[str(team_number)]

        if self.use_api:
            fetched = self._get_toa_data(f"/team/{team_number}")
            if isinstance(fetched, dict):
                short_name = fetched.get("team_name_short") or fetched.get("teamNameShort")
                nickname = short_name or fetched.get("nickname") or fetched.get("name") or fetched.get("team_name")
                if nickname:
                    try:
                        team_int = int(team_number)
                        self.team_names[team_int] = str(nickname)
                        # Also update persistent cache
                        _persistent_team_names[team_int] = str(nickname)
                    except (TypeError, ValueError):
                        self.team_names[str(team_number)] = str(nickname)
                    return str(nickname)

        return str(team_number)

    # Backwards-compatible alias used by the UI.
    def get_team_nickname(self, team_number):
        return self.get_team_name(team_number)

    def _update_team_names(self, teams_data) -> None:
        """Populate the team nickname cache from raw team entries."""
        global _persistent_team_names
        for team in teams_data or []:
            if not isinstance(team, dict):
                continue
            number = team.get("team_number")
            if number is None:
                continue
            nickname = team.get("team_name_short") or team.get("nickname") or team.get("name") or f"Team {number}"
            try:
                team_int = int(number)
                self.team_names[team_int] = str(nickname)
                # Also update persistent cache for future TOAManager instances
                _persistent_team_names[team_int] = str(nickname)
            except (TypeError, ValueError):
                self.team_names[str(number)] = str(nickname)

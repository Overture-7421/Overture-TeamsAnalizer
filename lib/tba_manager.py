"""
Manages interaction with The Blue Alliance (TBA) API.

This module provides a class to fetch event and team data from TBA,
and to manage a local cache of team names to avoid excessive API calls.
"""

import requests
import json
from pathlib import Path

BASE_URL = "https://www.thebluealliance.com/api/v3"
DATA_DIR = Path(__file__).resolve().parent


def _ensure_data_dir() -> None:
    """Make sure the cache directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

class TBAManager:
    """
    A manager for fetching and caching data from The Blue Alliance API.
    """
    def __init__(self, api_key=None, use_api=True):
        """
        Initializes the manager with a TBA authentication key.

        Args:
            api_key (str): Your TBA authentication key (X-TBA-Auth-Key).
        """
        self.api_key = api_key
        self.use_api = bool(use_api)
        if self.use_api:
            if not api_key:
                raise ValueError("TBA API Key is required when API access is enabled.")
            self.headers = {
                "X-TBA-Auth-Key": api_key,
                "Accept": "application/json"
            }
        else:
            self.headers = {}
        self.team_names = {}  # Cache for team number -> nickname mapping
        self.events_cache = {}
        self.team_cache = {}

    def _get_tba_data(self, endpoint):
        """
        Generic function to make a GET request to the TBA API.
        
        Args:
            endpoint (str): The API endpoint to request (e.g., "/status").

        Returns:
            dict or list or None: The JSON response from the API, or None if an error occurs.
        """
        if not self.use_api:
            print("[INFO] API access disabled. Using cached data only.")
            return None

        url = BASE_URL + endpoint
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raises an exception for 4xx/5xx status codes
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("[ERROR] TBA API request failed: Unauthorized. Please check your API key.")
            else:
                print(f"[ERROR] TBA API request failed with status {e.response.status_code}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] An error occurred during the TBA API request: {e}")
            return None

    def set_api_usage(self, enabled: bool) -> None:
        """Toggle whether API requests are allowed."""
        if enabled:
            if not self.api_key:
                raise ValueError("No API key configured; cannot enable API access.")
            self.headers = {
                "X-TBA-Auth-Key": self.api_key,
                "Accept": "application/json"
            }
        else:
            self.headers = {}
        self.use_api = bool(enabled)

    def get_events_for_year(self, year, force_refresh: bool = False):
        """
        Fetches a simplified list of all events for a given year.

        Args:
            year (int): The competition year.
            force_refresh (bool): If True, bypass cached data and hit the API (when enabled).

        Returns:
            list or None: A list of event dictionaries, or None on failure.
        """
        year = int(year)

        if not force_refresh:
            cached = self.events_cache.get(year)
            if cached:
                return cached

            saved = self.load_events_from_file(year)
            if saved is not None:
                self.events_cache[year] = saved
                return saved

        if not self.use_api:
            print(f"[INFO] Offline mode: no cached events found for {year}.")
            return None

        print(f"Fetching events for year {year}...")
        endpoint = f"/events/{year}/simple"
        events = self._get_tba_data(endpoint)
        if events is not None:
            self.events_cache[year] = events
            self.save_events_to_file(year, events)
        return events

    def get_teams_for_event(self, event_key, force_refresh: bool = False):
        """
        Fetches a list of all teams for a given event.

        Args:
            event_key (str): The TBA key for the event (e.g., "2024txho").
            force_refresh (bool): If True, bypass cached data and hit the API (when enabled).

        Returns:
            list or None: A list of team dictionaries, or None on failure.
        """
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
        endpoint = f"/event/{event_key}/teams/simple"
        teams = self._get_tba_data(endpoint)
        if teams is not None:
            self.team_cache[event_key] = teams
            self._update_team_names(teams)
            self.save_teams_to_file(event_key, teams)
        return teams

    def save_events_to_file(self, year: int, events_data):
        """Persist event listings for reuse when offline."""
        if events_data is None:
            return False

        _ensure_data_dir()
        filename = DATA_DIR / f"events_{year}.json"
        try:
            with filename.open("w", encoding="utf-8") as f:
                json.dump(events_data, f, indent=4)
            print(f"Successfully saved events to {filename}")
            return True
        except IOError as e:
            print(f"Error saving events to file: {e}")
            return False

    def load_events_from_file(self, year: int):
        """Load cached event listings if they exist."""
        filename = DATA_DIR / f"events_{year}.json"
        if not filename.exists():
            return None

        try:
            with filename.open("r", encoding="utf-8") as f:
                events = json.load(f)
            return events
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading events from {filename}: {e}")
            return None

    def save_teams_to_file(self, event_key, teams_data):
        """
        Saves the fetched team data to a local JSON file.

        Args:
            event_key (str): The event key, used for the filename.
            teams_data (list): The list of team data to save.
        """
        if teams_data is None:
            return False

        _ensure_data_dir()
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

    def load_teams_from_file(self, event_key):
        """
        Loads team data from a local JSON file and populates the team_names cache.

        Args:
            event_key (str): The event key to find the corresponding file.

        Returns:
            bool: True if the file was loaded successfully, False otherwise.
        """
        candidate_filenames = [
            DATA_DIR / f"tba_teams_{event_key}.json",
            DATA_DIR / f"teams_{event_key}.json"
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

            self.team_cache[event_key] = teams_data
            self._update_team_names(teams_data)
            print(f"Successfully loaded {len(teams_data)} teams from {target_file.name}")
            return teams_data
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing team data from {target_file}: {e}")
            return None

    def get_team_nickname(self, team_number):
        """
        Gets a team's nickname from the cache.

        Args:
            team_number (int): The team number.

        Returns:
            str: The team's nickname, or the team number as a string if not found.
        """
        try:
            team_key = int(team_number)
        except (TypeError, ValueError):
            team_key = None

        if team_key is not None and team_key in self.team_names:
            return self.team_names[team_key]

        # Fallback: also check string form in case cache was populated differently
        return self.team_names.get(str(team_number), str(team_number))

    def _update_team_names(self, teams_data):
        """Populate the team nickname cache from raw team entries."""
        for team in teams_data or []:
            number = team.get('team_number')
            if number is None:
                continue
            nickname = team.get('nickname') or team.get('name') or f"Team {number}"
            try:
                self.team_names[int(number)] = nickname
            except (TypeError, ValueError):
                self.team_names[str(number)] = nickname

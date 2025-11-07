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

class TBAManager:
    """
    A manager for fetching and caching data from The Blue Alliance API.
    """
    def __init__(self, api_key):
        """
        Initializes the manager with a TBA authentication key.

        Args:
            api_key (str): Your TBA authentication key (X-TBA-Auth-Key).
        """
        if not api_key:
            raise ValueError("TBA API Key is required.")
        
        self.headers = {
            "X-TBA-Auth-Key": api_key,
            "Accept": "application/json"
        }
        self.team_names = {}  # Cache for team number -> nickname mapping

    def _get_tba_data(self, endpoint):
        """
        Generic function to make a GET request to the TBA API.
        
        Args:
            endpoint (str): The API endpoint to request (e.g., "/status").

        Returns:
            dict or list or None: The JSON response from the API, or None if an error occurs.
        """
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

    def get_events_for_year(self, year):
        """
        Fetches a simplified list of all events for a given year.

        Args:
            year (int): The competition year.

        Returns:
            list or None: A list of event dictionaries, or None on failure.
        """
        print(f"Fetching events for year {year}...")
        endpoint = f"/events/{year}/simple"
        return self._get_tba_data(endpoint)

    def get_teams_for_event(self, event_key):
        """
        Fetches a list of all teams for a given event.

        Args:
            event_key (str): The TBA key for the event (e.g., "2024txho").

        Returns:
            list or None: A list of team dictionaries, or None on failure.
        """
        print(f"Fetching teams for event {event_key}...")
        endpoint = f"/event/{event_key}/teams/simple"
        return self._get_tba_data(endpoint)

    def save_teams_to_file(self, event_key, teams_data):
        """
        Saves the fetched team data to a local JSON file.

        Args:
            event_key (str): The event key, used for the filename.
            teams_data (list): The list of team data to save.
        """
        filename = DATA_DIR / f"teams_{event_key}.json"
        try:
            with filename.open("w", encoding="utf-8") as f:
                json.dump(teams_data, f, indent=4)
            print(f"Successfully saved team data to {filename}")
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
            return False

        try:
            with target_file.open("r", encoding="utf-8") as f:
                teams_data = json.load(f)

            updated_names = {}
            for team in teams_data:
                number = team.get('team_number')
                if number is None:
                    continue
                nickname = team.get('nickname') or team.get('name') or f"Team {number}"
                updated_names[int(number)] = nickname

            if not updated_names:
                print(f"No team entries found in {target_file}.")
                return False

            self.team_names.update(updated_names)
            print(f"Successfully loaded {len(updated_names)} teams from {target_file.name}")
            return True
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing team data from {target_file}: {e}")
            return False

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

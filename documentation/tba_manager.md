# TBA Manager (tba_manager.py)

## Overview

The `tba_manager.py` module provides integration with The Blue Alliance (TBA) API. It fetches team names, event data, and caches results for offline use.

## Location

```
lib/tba_manager.py
```

## Key Features

- **Team Data**: Fetch team names and nicknames
- **Event Data**: List events by year
- **Caching**: Save/load data for offline use
- **API Key Support**: Secure TBA API authentication

## Getting a TBA API Key

1. Visit [thebluealliance.com/account](https://www.thebluealliance.com/account)
2. Log in or create an account
3. Navigate to "Read API Keys"
4. Add a description (e.g., "Overture Alliance App")
5. Click "Add New Key"
6. Copy the generated `X-TBA-Auth-Key`

## Classes

### TBAManager

Main class for TBA API integration.

```python
from tba_manager import TBAManager

# Initialize with API key
tba = TBAManager(api_key="your_api_key_here", use_api=True)

# Initialize for offline mode
tba = TBAManager(api_key=None, use_api=False)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | TBA API key (X-TBA-Auth-Key) |
| `use_api` | `bool` | Enable API requests |

#### Methods

```python
# Get team nickname
nickname = tba.get_team_nickname("7421")
# Returns: "Team Overture" or None

# Get events for year
events = tba.get_events_for_year(2024)
# Returns: [{"key": "2024txho", "name": "Houston Championship", ...}]

# Get teams for event
teams = tba.get_teams_for_event("2024txho")
# Returns: [{"key": "frc7421", "nickname": "Team Overture", ...}]

# Load teams from file
success = tba.load_teams_from_file("2024txho")
# Returns: True if file exists and loaded

# Save teams to file
tba.save_teams_to_file("2024txho", teams_data)
# Saves to teams_2024txho.json

# Toggle API usage
tba.set_api_usage(True)  # Enable API
tba.set_api_usage(False)  # Offline mode
```

## Offline Mode

For environments without internet access:

### 1. Pre-download Data

On a machine with internet:

```python
tba = TBAManager(api_key="your_key", use_api=True)

# Download and save event teams
teams = tba.get_teams_for_event("2024txho")
tba.save_teams_to_file("2024txho", teams)
```

### 2. Copy Cache Files

Transfer JSON files to the offline machine:
- `events_2024.json`
- `teams_2024txho.json`

### 3. Use Offline Mode

```python
tba = TBAManager(api_key=None, use_api=False)
tba.load_teams_from_file("2024txho")

# Now team lookups work offline
nickname = tba.get_team_nickname("7421")
```

## Cache Files

### Events Cache

File: `events_YYYY.json` (e.g., `events_2024.json`)

```json
[
    {
        "key": "2024txho",
        "name": "FIRST Championship - Houston",
        "event_code": "txho",
        "year": 2024,
        "start_date": "2024-04-17",
        "end_date": "2024-04-20"
    },
    ...
]
```

### Teams Cache

File: `teams_<event_key>.json` (e.g., `teams_2024txho.json`)

```json
[
    {
        "key": "frc7421",
        "team_number": 7421,
        "nickname": "Team Overture",
        "name": "Overture 7421",
        "city": "Monterrey",
        "state_prov": "NL",
        "country": "Mexico"
    },
    ...
]
```

## Integration with Streamlit

In the Streamlit app:

```python
# Initialize in session state
if 'tba_manager' not in st.session_state:
    st.session_state.tba_manager = None

# Settings page
if st.button("Initialize TBA Manager"):
    try:
        st.session_state.tba_manager = TBAManager(
            api_key=st.session_state.tba_api_key,
            use_api=st.session_state.tba_use_api
        )
        st.success("TBA Manager initialized!")
    except ValueError as e:
        st.error(str(e))

# Use throughout app
if st.session_state.tba_manager:
    team_name = st.session_state.tba_manager.get_team_nickname("7421")
```

## Error Handling

```python
try:
    tba = TBAManager(api_key=None, use_api=True)
except ValueError as e:
    print(f"Error: {e}")
    # API key required for online mode

# Handle missing data
nickname = tba.get_team_nickname("99999")
if nickname is None:
    nickname = f"Team 99999"  # Fallback
```

## API Rate Limits

TBA has rate limits. Best practices:
- Cache data locally after fetching
- Use offline mode during events
- Don't fetch repeatedly in loops

## Dependencies

- `requests` - HTTP requests (optional)
- `json` - JSON parsing
- `pathlib` - File path handling

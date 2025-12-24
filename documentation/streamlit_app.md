# Streamlit App (streamlit_app.py)

## Overview

The `streamlit_app.py` module provides the web-based user interface for the Overture Teams Analyzer. It's built using Streamlit and offers a comprehensive dashboard for scouting data analysis.

## Location

```
lib/streamlit_app.py
```

## Key Features

- **Dashboard**: Quick statistics and team rankings overview
- **Data Management**: CSV upload, QR scanning, and data export
- **Team Statistics**: Detailed analysis with visualizations
- **Alliance Selector**: Alliance building and optimization
- **Honor Roll System**: Team competency scoring
- **Foreshadowing**: Match prediction simulation
- **TBA Integration**: The Blue Alliance API for team data

## Running the Application

### Development Mode

```bash
cd Overture-TeamsAnalizer
streamlit run lib/streamlit_app.py
```

### Production Mode

```bash
streamlit run lib/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true
```

### Access

- Local: `http://localhost:8501`
- Network: `http://<IP_ADDRESS>:8501`

## Navigation Pages

### 📊 Dashboard

Overview page with:
- Total matches and teams count
- Average overall score
- Alliance configuration count
- Top 10 teams ranking table
- Quick insights (top team, most consistent, best robot)

### 📁 Data Management

Four tabs for data operations:

1. **Upload Data**
   - CSV file upload
   - QR data paste
   - Default CSV status and reload controls

2. **QR Scanner**
   - Camera test
   - Headless mode instructions
   - Scanner configuration guidance

3. **View Raw Data**
   - Full dataset table view
   - Record count

4. **Export Data**
   - Raw data CSV export
   - Simplified ranking export

### 📈 Team Statistics

Three analysis tabs:

1. **Overall Rankings**
   - Comprehensive team statistics table
   - Performance visualization (scatter plot)

2. **Detailed Stats**
   - Single team selection mode
   - Multi-team comparison mode
   - Radar charts and bar comparisons
   - Match performance trends

3. **Simplified Ranking**
   - Key metrics summary table

### 🤝 Alliance Selector

Alliance building tools:
- Initialize/refresh alliance selector
- Auto-optimize picks
- Manual alliance configuration
- Captain and pick selections

### 🏆 Honor Roll System

Team competency scoring:
- Exam data import (Programming, Mechanical, Electrical, Competencies)
- Scoring weight configuration
- Team competency editor
- Honor Roll rankings table
- Team details inspector
- TierList export

### 🔮 Foreshadowing

Match prediction:
- Red/Blue alliance selection
- Quick and Monte Carlo simulations
- Score predictions and win probabilities
- Detailed score breakdowns
- Team performance profiles

### ⚙️ TBA Settings

The Blue Alliance integration:
- API key configuration
- Offline/online mode toggle
- Event selection
- Team data loading

## Session State Variables

Key session state variables:

```python
st.session_state.analizador          # AnalizadorRobot instance
st.session_state.alliance_selector   # AllianceSelector instance
st.session_state.school_system       # TeamScoring instance
st.session_state.tba_manager         # TBAManager instance
st.session_state.tba_api_key         # TBA API key
st.session_state.hot_reload_enabled  # Hot-reload toggle
```

## Configuration

### Application Config

Located at `config/config.json` or `lib/config/config.json`:

```json
{
    "app": {
        "title": "Alliance Simulator - Overture 7421",
        "icon": "🤖",
        "subtitle": "FRC 2025 REEFSCAPE",
        "team_name": "Team Overture 7421"
    },
    "scoring_weights": {
        "match_performance": 50,
        "pit_scouting": 30,
        "during_event": 20
    },
    "game": {
        "name": "REEFSCAPE 2025",
        "coral": {...},
        "algae": {...},
        "climb": {...}
    }
}
```

### Default Values

If config file is not found, defaults are used:
- Title: "Alliance Simulator - Overture 7421"
- Icon: 🤖
- Layout: Wide
- Scoring weights: 50/30/20

## Custom Styling

The app includes custom CSS for:
- Dark theme with purple accents
- Metric cards with gradients
- Enhanced buttons and tabs
- Custom sidebar styling
- Responsive data frames

## Dependencies

- `streamlit` - Web framework
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `matplotlib` - Static plots
- Engine modules (`engine.py`, `allianceSelector.py`, etc.)

## API Endpoints

Streamlit apps are single-page applications. For API access, consider:
- Using Streamlit's `st.experimental_get_query_params()`
- Exposing data through file exports
- Running a separate FastAPI service

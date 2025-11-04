# Running the Streamlit Web Application

## Quick Start

1. **Install dependencies** (if not already installed):
```bash
pip install -r requirements_web.txt
```

2. **Run the Streamlit app**:
```bash
streamlit run streamlit_app.py
```

3. **Access the application**:
The app will automatically open in your default web browser at `http://localhost:8501`

## Features

### 📊 Dashboard
- Quick overview of loaded data
- Key metrics and statistics
- Top 10 teams visualization

### 📁 Data Management
- Upload CSV files
- Paste QR code data
- View raw data
- Export data in various formats

### 📈 Team Statistics
- Overall team rankings
- Detailed team statistics
- Simplified ranking view
- Interactive visualizations

### 🤝 Alliance Selector
- Auto-optimize alliance selections
- Manual alliance configuration
- View recommendations
- Reset and reconfigure picks

### 🏆 Honor Roll System
- Configure scoring parameters
- Auto-populate from data
- View honor roll rankings
- Manage team competencies

### 🔮 Foreshadowing
- Match prediction (coming soon)
- Monte Carlo simulation
- Win probability analysis

## Navigation

Use the sidebar to navigate between different pages. Each page provides specific functionality for analyzing and managing FRC team data.

## Tips

- **Load data first**: Upload a CSV file or paste QR data before using other features
- **Refresh as needed**: Some actions require clicking "Initialize/Refresh" buttons
- **Export data**: Use export features to save your analysis results

## Troubleshooting

If you encounter issues:

1. **Module not found**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements_web.txt
   ```

2. **Data not loading**: Check that your CSV file matches the expected format

3. **Port already in use**: If port 8501 is in use, Streamlit will automatically try another port

## Differences from Desktop App

The web version provides the same core functionality as the desktop application but with:
- **Cleaner UI**: Streamlined interface optimized for web browsers
- **Better visualizations**: Interactive charts using Plotly
- **Easier sharing**: Can be deployed to share with team members
- **No installation**: Access from any device with a web browser (when deployed)

## Deployment

To deploy the app for team access:

1. **Streamlit Cloud** (recommended for teams):
   - Push code to GitHub
   - Connect to Streamlit Cloud
   - Deploy with one click

2. **Local Network**:
   ```bash
   streamlit run streamlit_app.py --server.address 0.0.0.0
   ```

3. **Docker** (advanced):
   - Create Dockerfile
   - Build and run container
   - Access from network

---

For more information, see the main README.md file.

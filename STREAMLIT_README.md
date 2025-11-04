# Running the Streamlit Web Application

## 🚀 Quick Start

### Option 1: Using Docker (Recommended)

The easiest way to run the application:

```bash
# Using Docker Compose
docker-compose up -d

# Access the app at http://localhost:8501
```

For detailed Docker deployment instructions, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Option 2: Local Python Installation

1. **Install dependencies**:
```bash
pip install -r requirements_web.txt
```

2. **Run the Streamlit app**:
```bash
streamlit run streamlit_app.py
```

3. **Access the application**:
The app will automatically open in your default web browser at `http://localhost:8501`

## ✨ New Features (v2.0 Enhanced UI)

### Visual Improvements
- **Modern Gradient Design**: Purple/blue gradient theme matching FRC branding
- **Enhanced Typography**: Clean, professional fonts with Google Fonts
- **Responsive Cards**: Hover effects and smooth transitions
- **Better Data Visualization**: Improved Plotly charts with custom styling
- **Team Badges**: Visual team identifiers throughout the interface
- **Quick Insights**: Dashboard now shows top team, most consistent, and best robot
- **Professional Footer**: Branded footer on all pages

### Performance Features
- **Docker Support**: One-command deployment with docker-compose
- **Health Checks**: Built-in monitoring for production deployments
- **Data Persistence**: Volume mounts for uploaded files
- **Optimized Build**: Smaller Docker image with .dockerignore

## ✨ New Features (v2.0 Enhanced UI)

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

### Docker Deployment (Recommended)

The application includes full Docker support for easy deployment:

```bash
# Quick start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Features:**
- ✅ One-command deployment
- ✅ Data persistence with volumes
- ✅ Health checks included
- ✅ Production-ready configuration
- ✅ Easy scaling and updates

For comprehensive Docker deployment instructions including cloud providers (AWS, GCP, Azure, DigitalOcean), 
reverse proxy setup, and SSL configuration, see **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)**

### Cloud Deployment Options

1. **Streamlit Cloud** (free, easy):
   - Push code to GitHub
   - Connect to Streamlit Cloud
   - Deploy with one click
   - Perfect for teams wanting instant deployment

2. **Docker on Cloud**:
   - AWS ECS/Fargate
   - Google Cloud Run
   - Azure Container Instances
   - DigitalOcean App Platform
   - See DOCKER_DEPLOYMENT.md for detailed instructions

3. **Local Network**:
   ```bash
   streamlit run streamlit_app.py --server.address 0.0.0.0
   ```
   Access from other devices on your network

## Production Considerations

- Use a reverse proxy (Nginx) for better performance
- Enable SSL/HTTPS with Let's Encrypt
- Configure firewall rules appropriately
- Set up monitoring and logging
- Regular backups of data volume

See DOCKER_DEPLOYMENT.md for security best practices and production setup guides.

---

For more information, see the main README.md file.

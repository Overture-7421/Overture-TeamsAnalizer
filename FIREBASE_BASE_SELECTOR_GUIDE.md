# Firebase Base Selector & Dark Theme - User Guide

## Overview
This update adds powerful Firebase data loading capabilities and a sleek dark theme to the Alliance Simulator Streamlit app.

## New Features

### 1. Firebase Base Selector
The app can now dynamically discover and load data from different Firebase collections (bases).

#### Supported Bases

**OffSeasonAllStar**
- Contains match data organized by team
- Each team document has a Matches subcollection
- Match documents contain detailed scouting data
- Automatically maps 25+ fields to analyzer format

**EquiposFRC**
- Contains team name mapping
- Document ID = team number (e.g., "7421")
- Document value = team name (e.g., "Overture 7421")
- Enriches all rankings with team names

### 2. Dark Theme
- Professional black background (#000000)
- White text with excellent contrast
- Purple accent colors maintained
- Optimized for extended viewing sessions
- All components styled consistently

## How to Use

### Step 1: Connect to Firebase

1. Navigate to **Data Management** page
2. Click on **Firebase** tab
3. If you see "Firebase SDK not installed", run:
   ```bash
   pip install firebase-admin google-cloud-firestore
   ```
4. Upload your Firebase service account credentials JSON file
5. Click "Connect to Firebase"
6. You should see "✅ Firebase Connected!"

### Step 2: Discover Available Bases

1. Click the **"🔍 Discover Available Bases"** button
2. The app will list all top-level collections in your Firestore
3. You should see bases like:
   - OffSeasonAllStar
   - EquiposFRC
   - And any other collections you have

### Step 3: Load OffSeasonAllStar Match Data

1. Select **"OffSeasonAllStar"** from the dropdown
2. You'll see: "📊 OffSeasonAllStar: Loads match data from team Matches subcollections"
3. Click **"📥 Load OffSeasonAllStar"**
4. Wait for the loading spinner
5. You'll see a summary like:
   ```
   Loaded 314 matches from 27 teams
   
   Warnings:
   - Team 9999 has no matches in Matches subcollection
   
   Defaulted fields:
   - Pickup Location: 15 instances
   - Coral HP Mistake: 42 instances
   ```
6. The app will reload and statistics will be available!

### Step 4: Load Team Names (Optional but Recommended)

1. Select **"EquiposFRC"** from the dropdown
2. Click **"📥 Load EquiposFRC"**
3. You'll see: "Loaded 27 team names"
4. Sample team names will be displayed
5. All rankings now show "Team Name (Team #)" format!

### Step 5: View Enhanced Statistics

1. Navigate to **Team Statistics** page
2. Check the **Overall Rankings** tab
3. Teams are now displayed as "Overture 7421 (7421)" instead of just "7421"
4. The **Simplified Ranking** tab also shows team names
5. Export functions include team names in CSV files

## Data Mapping

### OffSeasonAllStar Field Mapping

The system automatically maps Firestore field names to analyzer columns:

| Firestore Field | Analyzer Column |
|----------------|-----------------|
| SCOUTER INITIALS | Scouter Initials |
| ROBOT | Robot |
| FUTURE ALLIANCE IN QUALY? | Future Alliance |
| STARTING POSITION | Starting Position |
| NO SHOW | No Show |
| MOVED? | Moved (Auto) |
| CORAL L1 SCORED AUTO | Coral L1 (Auto) |
| CORAL L2 SCORED AUTO | Coral L2 (Auto) |
| CORAL L3 SCORED AUTO | Coral L3 (Auto) |
| CORAL L4 SCORED AUTO | Coral L4 (Auto) |
| BARGE ALGAE SCORED AUTO | Barge Algae (Auto) |
| PROCESSOR ALGAE SCORED AUTO | Processor Algae (Auto) |
| DISLODGED ALGAE? AUTO | Dislodged Algae (Auto) |
| AUTO FOUL | Foul (Auto) |
| DISLODGED ALGAE? TELEOP | Dislodged Algae (Teleop) |
| PICKUP LOCATION | Pickup Location |
| CORAL L1 SCORED TELEOP | Coral L1 (Teleop) |
| CORAL L2 SCORED TELEOP | Coral L2 (Teleop) |
| CORAL L3 SCORED TELEOP | Coral L3 (Teleop) |
| CORAL L4 SCORED TELEOP | Coral L4 (Teleop) |
| BARGE ALGAE SCORED TELEOP | Barge Algae (Teleop) |
| PROCESSOR ALGAE SCORED TELEOP | Processor Algae (Teleop) |
| CROSSED FIELD/PLAYED DEFENSE? | Crossed Field/Defense |
| TIPPED/FELL OVER? | Tipped/Fell |
| TOUCHED OPPOSING CAGE | Touched Opposing Cage |
| DIED? | Died |
| END POSITION | End Position |
| BROKE? | Broke |
| DEFENDED? | Defended |
| CORAL HP MISTAKE? | Coral HP Mistake |
| YELLOW/RED CARD | Yellow/Red Card |

### Default Values for Missing Fields

If a field is missing in a match document:

- **Numeric fields**: Default to `0`
- **Boolean fields**: Default to `False`
- **String fields**: Default to sensible values:
  - Robot: "1"
  - Starting Position: "Unknown"
  - Pickup Location: "Unknown"
  - End Position: "Unknown"
  - Yellow/Red Card: "None"

## Firestore Structure Requirements

### OffSeasonAllStar Structure
```
OffSeasonAllStar/
  ├── 7421/                    # Team number as document ID
  │   └── Matches/             # Subcollection
  │       ├── Match 1          # Match documents
  │       ├── Match 2
  │       └── Match 3
  ├── 254/
  │   └── Matches/
  │       ├── Match 1
  │       └── Match 2
  └── ...
```

Each Match document should contain the fields listed in the mapping table above.

### EquiposFRC Structure
```
EquiposFRC/
  ├── 7421                     # Team number as document ID
  │   └── name: "Overture 7421"  # Team name as field
  ├── 254
  │   └── name: "The Cheesy Poofs"
  └── ...
```

OR (simple structure):
```
EquiposFRC/
  ├── 7421: "Overture 7421"    # Direct string value
  ├── 254: "The Cheesy Poofs"
  └── ...
```

## Dark Theme Customization

If you want to adjust the dark theme colors, edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#667eea"          # Purple accent color
backgroundColor = "#000000"       # Main background (black)
secondaryBackgroundColor = "#1a1a1a"  # Secondary backgrounds
textColor = "#ffffff"             # Main text color
font = "sans serif"
```

## Troubleshooting

### "Firebase SDK not installed"
**Solution**: Install the required packages:
```bash
pip install firebase-admin google-cloud-firestore
```

### "No collections found in Firebase"
**Possible causes**:
1. Credentials don't have read access
2. Firestore database is empty
3. Wrong project credentials

**Solution**: Verify credentials and check Firebase Console

### "No data found in OffSeasonAllStar"
**Possible causes**:
1. Collection is empty
2. Team documents exist but Matches subcollection is empty
3. Field names don't match expected format

**Solution**: Check Firestore structure in Firebase Console

### Team names not showing after loading EquiposFRC
**Possible causes**:
1. EquiposFRC documents have wrong structure
2. Field name is not "name" or document is not a simple string

**Solution**: The system tries multiple field formats. Check console for warnings.

### Chart backgrounds are light instead of dark
**Solution**: The .streamlit/config.toml should be loaded automatically. Try:
1. Restart the Streamlit app
2. Clear browser cache
3. Verify .streamlit/config.toml exists

## Performance Tips

1. **Use session caching**: Once loaded, data stays in memory until you reload the app
2. **Load EquiposFRC first**: It's smaller and loads faster
3. **Check metadata**: Review warnings and missing fields to optimize your Firestore structure
4. **Use "Reload All Bases"**: Only needed if you add new collections

## Advanced Usage

### Loading Custom Collections

If you have other collections besides OffSeasonAllStar and EquiposFRC:

1. Discover bases to see them listed
2. Select the custom collection
3. Click "Load [collection name]"
4. The system will attempt to load it using the generic scouting_data format

### Exporting Data with Team Names

1. Load both OffSeasonAllStar and EquiposFRC
2. Go to **Data Management** → **Export Data**
3. Click "Export Simplified Ranking"
4. The downloaded CSV will include team names

## Security Best Practices

1. **Never commit Firebase credentials**: The .gitignore excludes .streamlit/secrets.toml
2. **Use read-only credentials**: Service account only needs Firestore read access
3. **Rotate credentials**: If credentials are exposed, regenerate them in Firebase Console

## Support

For issues or questions:
1. Check this guide
2. Review Firebase Console for data structure
3. Check browser console for detailed error messages
4. Verify Firebase Admin SDK is properly installed

## What's Next?

After loading your data, explore:
- **Team Statistics**: View detailed performance metrics with team names
- **Alliance Selector**: Build optimized alliances
- **Honor Roll System**: Rank teams by competencies
- **Export Data**: Download rankings with team names included

Enjoy the enhanced Alliance Simulator with Firebase integration and dark theme! 🤖🔥

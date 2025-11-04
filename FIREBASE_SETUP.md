# Firebase Integration Guide for Alliance Simulator

## Overview

The Alliance Simulator now supports Firebase Cloud Firestore as a NoSQL database backend. This allows you to:

- **Store scouting data in the cloud** - Access from anywhere
- **Real-time synchronization** - Multiple scouts can upload data simultaneously
- **Query and filter data** - Load specific teams or matches
- **Backup and restore** - Cloud-based data persistence
- **Maintain manual options** - CSV and QR scanning still work

## Firebase Setup

### Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or select an existing project
3. Follow the setup wizard to create your project

### Step 2: Enable Firestore Database

1. In your Firebase project, click "Firestore Database" in the left menu
2. Click "Create database"
3. Choose production mode or test mode:
   - **Production mode**: Requires authentication (more secure)
   - **Test mode**: Open access (easier for testing)
4. Select a location closest to your team

### Step 3: Generate Service Account Credentials

1. Click the gear icon ⚙️ → "Project settings"
2. Go to the "Service accounts" tab
3. Click "Generate new private key"
4. Save the JSON file securely (contains sensitive credentials)

**⚠️ Important Security Notes:**
- Never commit this file to Git
- Never share it publicly
- Store it in a secure location
- Add it to `.gitignore`

## Using Firebase in the App

### Connecting to Firebase

1. **In Streamlit App:**
   - Navigate to "📁 Data Management" → "🔥 Firebase" tab
   - Upload your Firebase credentials JSON file
   - Click "🔗 Connect to Firebase"
   - You should see "✅ Firebase Connected!"

2. **Using Environment Variable:**
   ```bash
   export FIREBASE_CREDENTIALS_PATH=/path/to/your/credentials.json
   streamlit run streamlit_app.py
   ```

3. **In Docker:**
   ```yaml
   # docker-compose.yml
   environment:
     - FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
   volumes:
     - ./firebase-credentials.json:/app/firebase-credentials.json:ro
   ```

### Loading Data from Firebase

#### Load All Data
```
1. Go to Firebase tab
2. Enter collection name (default: "scouting_data")
3. Click "📥 Load All Data"
4. Data is loaded and ready for analysis
```

#### Filter by Team
```
1. Enter team number in "Filter by Team #"
2. Click "📥 Load Team Data"
3. Only that team's data is loaded
```

#### Filter by Match
```
1. Enter match number in "Filter by Match #"
2. Click "📥 Load Match Data"
3. Only that match's data is loaded
```

### Uploading Data to Firebase

```
1. Load data using CSV or QR scanner (manual methods)
2. Go to Firebase tab
3. Enter collection name
4. Click "📤 Upload Current Data to Firebase"
5. Data is synchronized to cloud
```

### Data Flow Options

#### Option 1: Firebase as Primary Source
```
Scouts → Firebase (direct) → Load in App → Analyze
```
- Scouts upload directly to Firebase using mobile apps
- Analysts load from Firebase for analysis
- Real-time collaboration

#### Option 2: Manual Upload to Firebase
```
Scouts → QR/CSV → Load in App → Upload to Firebase → Share
```
- Traditional scouting workflow
- Upload to Firebase for backup/sharing
- Other team members can access

#### Option 3: Hybrid (Recommended)
```
Scouts → QR/CSV (local backup) + Firebase (cloud)
Analysts → Load from Firebase or CSV
```
- Best of both worlds
- Local backup + cloud sync
- Works offline and online

## Data Structure

### Firestore Collections

**Collection:** `scouting_data` (default)
- Contains all scouting records
- Each document represents one match observation

**Collection:** `configurations`
- Stores app configurations
- Column mappings, team settings, etc.

**Collection:** `statistics_cache`
- Cached computed statistics
- Improves performance for repeated queries

### Document Structure

Each scouting record contains:
```json
{
  "Team Number": 1234,
  "Match Number": 5,
  "Coral L1 Scored": 8,
  "Coral L2 Scored": 6,
  // ... other scouting fields
  "uploaded_at": "2025-01-15T10:30:00Z",
  "doc_id": "1234_5_0_timestamp"
}
```

## Security Best Practices

### 1. Firestore Security Rules

In Firebase Console → Firestore → Rules, set appropriate rules:

**For Testing:**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.time < timestamp.date(2025, 12, 31);
    }
  }
}
```

**For Production:**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only authenticated users can read/write
    match /scouting_data/{document} {
      allow read, write: if request.auth != null;
    }
    
    // Only team admins can clear data
    match /configurations/{document} {
      allow read: if request.auth != null;
      allow write: if request.auth.token.admin == true;
    }
  }
}
```

### 2. Credentials Management

**DO:**
- Store credentials outside the repository
- Use environment variables
- Restrict file permissions (chmod 600)
- Use Firebase Authentication for multi-user access

**DON'T:**
- Commit credentials to Git
- Share credentials publicly
- Use test mode in production
- Give write access to untrusted users

### 3. Data Validation

The app validates data before upload:
- Required fields are present
- Team numbers are valid
- Match numbers are reasonable
- Data types are correct

## Advanced Features

### Real-time Collaboration

Multiple users can:
1. Upload data simultaneously
2. Load latest data instantly
3. See updates in real-time

### Offline Support

The app works offline:
1. Use CSV/QR methods when offline
2. Upload to Firebase when online
3. Data is synchronized automatically

### Data Migration

**From CSV to Firebase:**
```python
# In Python script
from firebase_integration import FirebaseManager
import pandas as pd

# Load CSV
df = pd.read_csv('scouting_data.csv')
data = df.to_dict('records')

# Upload to Firebase
fb = FirebaseManager('credentials.json')
fb.upload_scouting_data(data)
```

**From Firebase to CSV:**
```python
# In the app or script
fb = FirebaseManager('credentials.json')
data = fb.get_all_scouting_data()

# Convert to DataFrame and save
df = pd.DataFrame(data)
df.to_csv('exported_data.csv', index=False)
```

## Troubleshooting

### Connection Issues

**Error: "Firebase not connected"**
- Check credentials file is valid JSON
- Verify Firebase project is active
- Check internet connection

**Error: "Permission denied"**
- Update Firestore security rules
- Check service account has proper permissions
- Verify credentials are not expired

### Data Loading Issues

**No data returned**
- Check collection name is correct
- Verify data exists in Firebase Console
- Try querying with filters

**Slow loading**
- Use filters to load less data
- Check internet speed
- Consider using statistics cache

### Upload Issues

**Upload fails**
- Check write permissions
- Verify data format is correct
- Check Firestore quota limits

## Firestore Quotas (Free Tier)

- **Stored data:** 1 GB
- **Document reads:** 50,000/day
- **Document writes:** 20,000/day
- **Document deletes:** 20,000/day

For competition use, this is usually sufficient. Upgrade to Blaze plan if needed.

## Integration with Mobile Apps

You can build mobile scouting apps that write directly to Firebase:

```javascript
// Example: Web app uploading to Firebase
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc } from 'firebase/firestore';

const db = getFirestore(app);

// Upload scouting data
await addDoc(collection(db, 'scouting_data'), {
  'Team Number': 1234,
  'Match Number': 5,
  // ... other fields
});
```

Then the Alliance Simulator can load this data instantly!

## Cost Estimation

For a typical FRC regional with 40 teams, 80 matches:
- ~3,200 scouting records (40 teams × 80 matches)
- ~500 KB per match data
- Total storage: ~1.6 MB
- Reads during event: ~10,000
- Writes during event: ~3,200

**Cost: FREE** (well within free tier limits)

## Support

For Firebase-specific issues:
- [Firebase Documentation](https://firebase.google.com/docs/firestore)
- [Firestore Pricing](https://firebase.google.com/pricing)
- [Firebase Console](https://console.firebase.google.com/)

For Alliance Simulator issues:
- Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- See [STREAMLIT_README.md](STREAMLIT_README.md)
- Create an issue on GitHub

---

**🔥 Firebase + Alliance Simulator = Real-time Scouting Excellence**

*Team Overture 7421 - FRC 2025 REEFSCAPE*

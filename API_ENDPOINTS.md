# Store Visit Tracker API Endpoints

## Overview
This document describes all available API endpoints for the Store Visit Tracker backend.

---

## Endpoints

### 1. Get Visit Briefs (List View)
**GET** `/api/visits`

Fetch a list of visit briefs (summaries) for a specific store or all recent visits.

**Query Parameters:**
- `storeNbr` (optional): Store number to filter by. If provided, returns the last 3 visits for that store. If omitted, returns the last 100 visits across all stores.

**Response:** Array of visit objects
```json
[
  {
    "id": 123,
    "storeNbr": "1234",
    "calendar_date": "2024-12-18",
    "rating": "Green",
    "store_notes": "Store looks great...",
    "mkt_notes": "Market is competitive...",
    "good": "Strong customer service\nClean floor",
    "top_3": "Work on features\nImprove displays",
    "created_at": "2024-12-18T15:30:45.123456"
  },
  ...
]
```

**Example Usage (Android):**
```java
OkHttpClient client = new OkHttpClient();
Request request = new Request.Builder()
    .url("https://your-api.com/api/visits?storeNbr=1234")
    .build();

client.newCall(request).enqueue(new Callback() {
    @Override
    public void onResponse(Call call, Response response) throws IOException {
        String jsonBody = response.body().string();
        // Parse and display the list of visit briefs
    }
});
```

---

### 2. Get Full Visit Details ⭐ NEW
**GET** `/api/visit/<visit_id>`

Fetch the complete details for a single visit. Use this endpoint when a user clicks on a visit brief to view the full information.

**Path Parameters:**
- `visit_id` (required): The numeric ID of the visit to retrieve

**Response:** Single visit object with all details
```json
{
  "id": 123,
  "storeNbr": "1234",
  "calendar_date": "2024-12-18",
  "rating": "Green",
  "store_notes": "Store looks great, well zoned. Heidi doing excellent job with team. Backroom organized and clean.",
  "mkt_notes": "Market is very competitive. New competitor 2 miles away.",
  "good": "Strong customer service\nClean sales floor\nTeam morale high",
  "top_3": "Work on features - need more endcaps filled\nApparel folding needs attention",
  "sales_comp_yest": 5.2,
  "sales_index_yest": 102,
  "sales_comp_wtd": null,
  "sales_index_wtd": null,
  "sales_comp_mtd": 3.1,
  "sales_index_mtd": 101,
  "vizpick": 85.5,
  "overstock": 12,
  "picks": 45,
  "vizfashion": 92.0,
  "modflex": 88.5,
  "tag_errors": 3,
  "mods": 156,
  "pcs": 2340,
  "pinpoint": 91.2,
  "ftpr": 96.8,
  "presub": 87.5,
  "created_at": "2024-12-18T15:30:45.123456"
}
```

**Status Codes:**
- `200`: Success - visit found
- `404`: Visit not found (invalid visit_id)
- `500`: Server error

**Example Usage (Android):**
```java
// When user clicks on a visit brief
int visitId = visitBrief.getId(); // Get ID from the brief

OkHttpClient client = new OkHttpClient();
Request request = new Request.Builder()
    .url("https://your-api.com/api/visit/" + visitId)
    .build();

client.newCall(request).enqueue(new Callback() {
    @Override
    public void onResponse(Call call, Response response) throws IOException {
        if (response.code() == 200) {
            String jsonBody = response.body().string();
            // Parse and display the full visit details
            VisitDetail fullVisit = parseJson(jsonBody);
            showVisitDetailScreen(fullVisit);
        } else if (response.code() == 404) {
            showError("Visit not found");
        }
    }
});
```

---

### 3. Analyze Visit (Image Upload)
**POST** `/api/analyze-visit`

Upload an image of handwritten store visit notes and get AI-powered transcription and analysis.

**Request Body:**
```json
{
  "image_data": "base64-encoded-image-data",
  "mime_type": "image/jpeg"
}
```

**Response:** Parsed visit data ready for save
```json
{
  "storeNbr": "1234",
  "calendar_date": "2024-12-18",
  "rating": "Green",
  "store_notes": [...],
  "mkt_notes": [...],
  "good": [...],
  "top_3": [...],
  "metrics": {...}
}
```

---

### 4. Save Visit
**POST** `/api/save-visit`

Save a new visit record to the database.

**Request Body:**
```json
{
  "storeNbr": "1234",
  "calendar_date": "2024-12-18",
  "rating": "Green",
  "store_notes": ["Note 1", "Note 2"],
  "mkt_notes": ["Market note 1"],
  "good": ["Good thing 1"],
  "top_3": ["Top issue 1"],
  "metrics": {
    "sales_comp_yest": 5.2,
    "vizpick": 85.5,
    ...
  }
}
```

**Response:**
```json
{
  "message": "Visit saved successfully",
  "data": {...}
}
```

---

### 5. Check Duplicate Visit
**GET** `/api/check-duplicate`

Check if a visit already exists for a specific store on a specific date.

**Query Parameters:**
- `storeNbr` (required): Store number
- `calendar_date` (required): Date in YYYY-MM-DD format

**Response:**
```json
{
  "is_duplicate": false,
  "existing_records": []
}
```

---

### 6. Get Summary
**GET** `/api/summary`

Get a summary of recent visits grouped by store.

**Response:**
```json
[
  {
    "storeNbr": "1234",
    "recent_visits": [
      {"rating": "Green", "calendar_date": "2024-12-18"},
      {"rating": "Yellow", "calendar_date": "2024-12-15"}
    ]
  },
  ...
]
```

---

### 7. Get Market Notes
**GET** `/api/market-notes`

Get all market notes from all visits with their completion status.

**Response:**
```json
[
  {
    "visit_id": 123,
    "store_nbr": "1234",
    "calendar_date": "2024-12-18",
    "note_text": "Market is competitive",
    "completed": false
  },
  ...
]
```

---

### 8. Toggle Market Note Status
**POST** `/api/market-notes/toggle`

Mark a market note as completed or incomplete.

**Request Body:**
```json
{
  "visit_id": 123,
  "note_text": "Market is competitive",
  "completed": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Market note status updated"
}
```

---

## Integration Guide for Android App

### Step 1: Display Visit Briefs
Use endpoint #1 to fetch and display a list of visit briefs when user searches for a store.

### Step 2: Handle Click on Visit Brief
When user clicks on a visit brief:
1. Extract the `id` field from the clicked visit object
2. Call endpoint #2 with that ID: `GET /api/visit/{id}`
3. Display the full visit details in a detail screen/fragment

### Step 3: Display Full Visit Details
The full visit endpoint returns:
- All metrics (sales, operational, etc.)
- Complete store notes (not truncated)
- Market notes
- What's working well
- Top 3 opportunities
- Visit metadata (date, rating, created_at)

### Example Android Implementation Flow

```java
// In your VisitListFragment or Activity
private void loadVisits(String storeNumber) {
    // Use endpoint #1
    apiClient.getVisits(storeNumber, new Callback() {
        public void onResponse(List<VisitBrief> visits) {
            // Display list of briefs
            visitAdapter.setData(visits);
        }
    });
}

// In your click listener for a visit brief
private void onVisitBriefClicked(VisitBrief brief) {
    // Extract the ID and fetch full details
    apiClient.getVisitDetail(brief.getId(), new Callback() {
        public void onResponse(VisitDetail full) {
            // Navigate to detail screen and pass the full object
            Intent intent = new Intent(this, VisitDetailActivity.class);
            intent.putExtra("visit", full);
            startActivity(intent);
        }
    });
}
```

---

## Notes

- All dates are returned in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss.SSSSSS)
- All text fields with newline-separated values (like `good`, `top_3`, `store_notes`) are stored as plain text with `\n` separators. Consider parsing them into arrays on the client side for better UI presentation.
- Metrics that are null indicate those values were not recorded for that visit
- The `id` field in the list response is the unique identifier needed to fetch full details
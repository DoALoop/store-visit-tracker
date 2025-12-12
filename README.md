Python Store Visit Tracker (Google Cloud Version)

This is a web application built with Python (Flask) that allows you to log store visits and use Vertex AI to parse handwritten notes from an image. All data is stored in Google BigQuery.

Setup Instructions

This version requires a Google Cloud Project and a Service Account for authentication.

1. Google Cloud Project Setup

Create a Project: Go to the Google Cloud Console and create a new project (or use an existing one). Note your Project ID.

Enable APIs: In your project, go to "APIs & Services" > "Library" and enable the following two APIs:

Vertex AI API

BigQuery API

2. Create BigQuery Table

In the Cloud Console, navigate to BigQuery.

Create a Dataset: In the "Explorer" panel, click the three dots next to your project ID and select "Create dataset".

Dataset ID: Give it a name, like store_tracker.

Location: Choose a location (e.g., us-central1).

Create a Table: Click the three dots next to your new dataset and select "Create table".

Table name: Give it a name, like visits.

Switch to the "Query" editor and paste the following SQL to create the table with the correct schema. Replace the table name in the first line with your own project/dataset/table ID.

CREATE TABLE `your-project-id.your-dataset-name.your-table-name` (
  id STRING OPTIONS(description="Unique UUID for the visit log"),
  visitDate DATE,
  storeNumber INT64,
  rating STRING,
  storeNotes STRING,
  goodNotes STRING,
  top3GoDos STRING,
  needsFromMe STRING,
  createdAt TIMESTAMP
);


Run the query to create the table.

3. Create Service Account

Go to "IAM & Admin" > "Service Accounts".

Click "Create Service Account".

Give it a name (e.g., store-tracker-sa).

Grant Roles: Assign the following roles to this service account:

Vertex AI User (for processing notes)

BigQuery Data Editor (to read/write data)

BigQuery Job User (to run queries)

Click "Done".

Find your new service account, click the three dots under "Actions", and select "Manage keys".

Click "Add Key" > "Create new key".

Choose JSON and click "Create". A JSON key file will download.

4. Set Up Your Project

Save the app.py, requirements.txt, and README.md files into a new folder on your server (e.g., store-tracker-app).

CRITICAL: Inside that folder, create a new folder named templates.

Move index.html inside the templates folder.

Move the downloaded JSON key file into the main folder (alongside app.py).

Create a file named .env in the main folder.

Open the .env file and add the following, filling in your specific values:

# 1. Path to your service account key file
GOOGLE_APPLICATION_CREDENTIALS="your-key-file-name.json"

# 2. Your GCP Project ID
PROJECT_ID="your-project-id"

# 3. Your BigQuery Dataset & Table names
BIGQUERY_DATASET="store_tracker"
BIGQUERY_TABLE="visits"

# 4. The location for Vertex AI (must match your dataset)
LOCATION="us-central1"


5. Install Python Dependencies

Open a terminal in your project folder.

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`


Install the new libraries:

pip install -r requirements.txt


6. Run the Application

In your terminal, run the app:

python app.py


Open http://127.0.0.1:5000 in your browser.
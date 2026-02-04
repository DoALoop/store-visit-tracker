#!/usr/bin/env python3
"""Import contacts from CSV file into the database."""

import csv
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', '192.168.0.9')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'store_visits')
DB_USER = os.getenv('DB_USER', 'store_tracker')
DB_PASSWORD = os.getenv('DB_PASSWORD')

CSV_FILE = '/Users/tjbarnh/Downloads/Contact List-Grid view.csv'

def import_contacts():
    # Read CSV
    contacts = []
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Name', '').strip()
            if not name:
                continue

            # Map CSV columns to database columns
            contact = {
                'name': name,
                'title': row.get('Rank', '').strip() or None,  # Rank -> title
                'department': row.get('Title', '').strip() or None,  # Title -> department (what they oversee)
                'reports_to': row.get('Reporting to', '').strip() or None,
                'phone': row.get('Phone', '').strip() or None,
                'email': row.get('Email', '').strip() or None,
                'notes': None
            }

            # Add status and % time to notes if present
            status = row.get('Status', '').strip()
            pct_time = row.get('% Time', '').strip()
            notes_parts = []
            if status:
                notes_parts.append(f"Status: {status}")
            if pct_time:
                notes_parts.append(f"% Time: {pct_time}")
            if notes_parts:
                contact['notes'] = '; '.join(notes_parts)

            contacts.append(contact)

    print(f"Read {len(contacts)} contacts from CSV")

    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    try:
        cursor = conn.cursor()

        # Insert contacts
        insert_query = """
            INSERT INTO contacts (name, title, department, reports_to, phone, email, notes)
            VALUES %s
            ON CONFLICT DO NOTHING
        """

        values = [
            (c['name'], c['title'], c['department'], c['reports_to'], c['phone'], c['email'], c['notes'])
            for c in contacts
        ]

        execute_values(cursor, insert_query, values)
        conn.commit()

        print(f"Imported {cursor.rowcount} contacts successfully!")

        cursor.close()
    except Exception as e:
        conn.rollback()
        print(f"Error importing contacts: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    import_contacts()

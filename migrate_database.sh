#!/bin/bash

# Database migration script to add metrics columns
# Run this script to add the new metrics columns to your existing database

set -e  # Exit on any error

echo "🔄 Running database migration to add metrics columns..."
echo ""

# Database connection info
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-store_visits}"
DB_USER="${DB_USER:-store_tracker}"

echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

read -p "Continue with migration? (y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled."
    exit 1
fi

# Run the migration SQL
echo "📝 Adding metrics columns..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f add_metrics_columns.sql

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "New columns added:"
echo "  - sales_comp_yest, sales_index_yest"
echo "  - sales_comp_wtd, sales_index_wtd"
echo "  - sales_comp_mtd, sales_index_mtd"
echo "  - vizpick, overstock, picks, vizfashion"
echo "  - modflex, tag_errors, mods, pcs"
echo "  - pinpoint, ftpr, presub"
echo ""

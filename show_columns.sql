-- SQL script to show all columns in the store_visits table

-- Show table structure with column names, types, and nullable info
\d+ store_visits

-- Alternative: Query the information schema for detailed column info
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM
    information_schema.columns
WHERE
    table_name = 'store_visits'
ORDER BY
    ordinal_position;

-- Count how many visits have data in each metric column
SELECT
    COUNT(*) as total_visits,
    COUNT(sales_comp_yest) as has_sales_comp_yest,
    COUNT(sales_index_yest) as has_sales_index_yest,
    COUNT(sales_comp_wtd) as has_sales_comp_wtd,
    COUNT(sales_index_wtd) as has_sales_index_wtd,
    COUNT(sales_comp_mtd) as has_sales_comp_mtd,
    COUNT(sales_index_mtd) as has_sales_index_mtd,
    COUNT(vizpick) as has_vizpick,
    COUNT(overstock) as has_overstock,
    COUNT(picks) as has_picks,
    COUNT(vizfashion) as has_vizfashion,
    COUNT(modflex) as has_modflex,
    COUNT(tag_errors) as has_tag_errors,
    COUNT(mods) as has_mods,
    COUNT(pcs) as has_pcs,
    COUNT(pinpoint) as has_pinpoint,
    COUNT(ftpr) as has_ftpr,
    COUNT(presub) as has_presub
FROM
    store_visits;

-- =====================================================================
-- TiendaDB v1.0 — Planted Problems
-- =====================================================================
-- This script plants 18 problems intentionally for the PgGuardian project.
-- Each problem is marked with its ID (H01-H18) for evaluation.
--
-- DO NOT share this file with students. The master list is in
-- /docs/HALLAZGOS_v1.md (instructor only).
-- =====================================================================

SET client_min_messages = WARNING;

-- =====================================================================
-- CATEGORY 1: INDEXES
-- =====================================================================

-- ---------------------------------------------------------------------
-- H01: orders.customer_id has NO index
-- (foreign key without supporting index — causes seq scan on JOINs)
-- Already not created in 01_schema.sql. Just confirm it doesn't exist.
-- ---------------------------------------------------------------------
DROP INDEX IF EXISTS idx_orders_customer_id;

-- ---------------------------------------------------------------------
-- H02: Duplicate index on products(category_id)
-- We already have idx_products_category_id from schema.
-- Add a duplicate with a different name.
-- ---------------------------------------------------------------------
CREATE INDEX idx_products_category_dup ON products(category_id);

-- ---------------------------------------------------------------------
-- H03: Unused index on customers.birth_date
-- Created but never queried. Detector should flag idx_scan = 0
-- ---------------------------------------------------------------------
CREATE INDEX idx_customers_birth_date_unused ON customers(birth_date);

-- ---------------------------------------------------------------------
-- H04: Missing partial index on orders WHERE status = 'pending'
-- 95% of orders are 'pending'. Most queries filter by this.
-- Detector should suggest a partial index.
-- ---------------------------------------------------------------------
-- (Nothing to plant; the absence IS the problem)

-- ---------------------------------------------------------------------
-- H05: Missing covering index for frequent report query
-- SELECT id, total, order_date FROM orders WHERE customer_id = ?
-- Detector should suggest INCLUDE(total, order_date) on customer_id index
-- ---------------------------------------------------------------------
-- (Nothing to plant; the absence IS the problem)


-- =====================================================================
-- CATEGORY 2: BLOAT AND MAINTENANCE
-- =====================================================================

-- ---------------------------------------------------------------------
-- H06: event_log has severe bloat (~40%)
-- Simulate by performing many UPDATE+DELETE cycles
-- ---------------------------------------------------------------------
-- Disable autovacuum temporarily on this table so the dead tuples accumulate
ALTER TABLE event_log SET (autovacuum_enabled = false);

-- Generate bloat by updating then deleting many rows
DO $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 1..5 LOOP
        UPDATE event_log SET event_data = event_data || jsonb_build_object('iteration', i)
        WHERE id IN (SELECT id FROM event_log ORDER BY random() LIMIT 30000);
    END LOOP;

    -- Delete 30% to leave dead tuples
    DELETE FROM event_log WHERE id IN (SELECT id FROM event_log ORDER BY random() LIMIT 60000);
END $$;

-- Re-enable so future operations are normal, but bloat already accumulated
ALTER TABLE event_log SET (autovacuum_enabled = true);

-- ---------------------------------------------------------------------
-- H07: autovacuum DISABLED at table level on inventory
-- (this is a real misconfig because inventory is updated very often)
-- ---------------------------------------------------------------------
ALTER TABLE inventory SET (autovacuum_enabled = false);

-- ---------------------------------------------------------------------
-- H08: reviews has many dead tuples accumulated (~50%)
-- Different mechanism than H06: simulate via repeated UPDATE that
-- doesn't change indexed columns (HOT-eligible) but volume is huge
-- ---------------------------------------------------------------------
ALTER TABLE reviews SET (autovacuum_enabled = false);

DO $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 1..3 LOOP
        UPDATE reviews SET comment = comment || ' [edited ' || i || ']'
        WHERE id IN (SELECT id FROM reviews ORDER BY random() LIMIT 15000);
    END LOOP;
END $$;

ALTER TABLE reviews SET (autovacuum_enabled = true);


-- =====================================================================
-- CATEGORY 3: PROBLEMATIC QUERIES (logged via pg_stat_statements)
-- =====================================================================
-- The following queries are run multiple times to register in
-- pg_stat_statements. Detectors should pick them up from there.

-- Reset stats first to get clean data
SELECT pg_stat_statements_reset();

-- ---------------------------------------------------------------------
-- H09: Query with seq scan on orders (caused by missing H01 index)
-- This same query benefits from creating the H01 index.
-- We use prepared statements / direct calls so pg_stat_statements
-- registers the individual query, not the wrapping DO block.
-- ---------------------------------------------------------------------
SELECT count(*) FROM orders WHERE customer_id = 1;
SELECT count(*) FROM orders WHERE customer_id = 100;
SELECT count(*) FROM orders WHERE customer_id = 250;
SELECT count(*) FROM orders WHERE customer_id = 500;
SELECT count(*) FROM orders WHERE customer_id = 750;
SELECT count(*) FROM orders WHERE customer_id = 1000;
SELECT count(*) FROM orders WHERE customer_id = 1500;
SELECT count(*) FROM orders WHERE customer_id = 2000;
SELECT count(*) FROM orders WHERE customer_id = 2500;
SELECT count(*) FROM orders WHERE customer_id = 3000;
SELECT count(*) FROM orders WHERE customer_id = 3500;
SELECT count(*) FROM orders WHERE customer_id = 4000;
SELECT count(*) FROM orders WHERE customer_id = 4500;
SELECT count(*) FROM orders WHERE customer_id = 5000;
SELECT count(*) FROM orders WHERE customer_id = 5500;
SELECT count(*) FROM orders WHERE customer_id = 6000;
SELECT count(*) FROM orders WHERE customer_id = 6500;
SELECT count(*) FROM orders WHERE customer_id = 7000;
SELECT count(*) FROM orders WHERE customer_id = 7500;
SELECT count(*) FROM orders WHERE customer_id = 8000;
SELECT count(*) FROM orders WHERE customer_id = 8500;
SELECT count(*) FROM orders WHERE customer_id = 9000;
SELECT count(*) FROM orders WHERE customer_id = 9500;
SELECT count(*) FROM orders WHERE customer_id = 1234;
SELECT count(*) FROM orders WHERE customer_id = 5678;
SELECT count(*) FROM orders WHERE customer_id = 9876;
SELECT count(*) FROM orders WHERE customer_id = 4321;
SELECT count(*) FROM orders WHERE customer_id = 8765;
SELECT count(*) FROM orders WHERE customer_id = 2468;
SELECT count(*) FROM orders WHERE customer_id = 1357;

-- ---------------------------------------------------------------------
-- H10: Mismatch estimated vs actual rows on products
-- Cause: stale stats. We INSERT a lot of new rows but DON'T analyze.
-- ---------------------------------------------------------------------
-- (We DON'T DELETE old rows — that violates FKs. We only insert.)

INSERT INTO products (sku, name, description, category_id, price, cost, weight_kg, is_active)
SELECT
    'SKU-NEW-' || i,
    'New Product ' || i,
    'New product description with extra content to be detected',
    1 + (i % 50),
    (random() * 1000)::numeric(10, 2),
    (random() * 500)::numeric(10, 2),
    (random() * 5)::numeric(8, 3),
    TRUE
FROM generate_series(1, 5000) i;

-- INTENTIONALLY no ANALYZE here so stats become stale
-- The detector should notice rows estimated (~1000) vs actual (~6000)

-- Run a query that would trigger the planner to use stale stats
-- (run multiple times so it shows up in pg_stat_statements)
SELECT count(*) FROM products WHERE category_id = 1 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 5 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 10 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 15 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 20 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 25 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 30 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 35 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 40 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 45 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 50 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 12 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 23 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 34 AND is_active = TRUE;
SELECT count(*) FROM products WHERE category_id = 47 AND is_active = TRUE;

-- ---------------------------------------------------------------------
-- H11: Query causing sort spill to disk (work_mem too low)
-- These queries spill given work_mem=4MB (set in postgresql.conf for H14).
-- Note: if testing in a session without setting work_mem, won't spill.
-- ---------------------------------------------------------------------
-- Reporting query that aggregates and sorts ALL groups (no LIMIT cardinality reduction)
SET work_mem = '4MB';

SELECT order_id, sum(subtotal) AS total
FROM order_items
GROUP BY order_id
ORDER BY total DESC;

SELECT id, total, order_date
FROM orders
ORDER BY total DESC, order_date;

SELECT o.id, c.full_name, o.total
FROM orders o
JOIN customers c ON c.id = o.customer_id
ORDER BY o.total DESC;

RESET work_mem;

-- ---------------------------------------------------------------------
-- H12: Query with LIKE '%text%' on products.description
-- Anti-pattern: leading wildcard prevents index usage
-- ---------------------------------------------------------------------
SELECT count(*) FROM products WHERE description LIKE '%premium%';
SELECT count(*) FROM products WHERE description LIKE '%special%';
SELECT count(*) FROM products WHERE description LIKE '%detailed%';
SELECT count(*) FROM products WHERE description LIKE '%quality%';
SELECT count(*) FROM products WHERE description LIKE '%new%';
SELECT count(*) FROM products WHERE description LIKE '%edition%';
SELECT count(*) FROM products WHERE description LIKE '%features%';
SELECT count(*) FROM products WHERE description LIKE '%product%';
SELECT count(*) FROM products WHERE description LIKE '%description%';
SELECT count(*) FROM products WHERE description LIKE '%detect%';


-- =====================================================================
-- CATEGORY 4: CONFIGURATION
-- =====================================================================

-- ---------------------------------------------------------------------
-- H13: shared_buffers too low (128MB) for the dataset size
-- Set in postgresql.conf at container level (see docker-compose.yml)
-- ---------------------------------------------------------------------
-- (configured externally)

-- ---------------------------------------------------------------------
-- H14: work_mem too low (4MB) — causes H11 sort to spill
-- Set in postgresql.conf at container level
-- ---------------------------------------------------------------------
-- (configured externally)

-- ---------------------------------------------------------------------
-- H15: pg_stat_statements is loaded but track is set to 'none'
-- so most queries don't get tracked properly
-- ---------------------------------------------------------------------
-- We use a more subtle variant: pg_stat_statements.max is set very low
-- (configured externally)

-- ---------------------------------------------------------------------
-- H16: log_min_duration_statement = -1 (slow queries not logged)
-- Set in postgresql.conf at container level
-- ---------------------------------------------------------------------
-- (configured externally)


-- =====================================================================
-- CATEGORY 5: GENERAL HEALTH
-- =====================================================================

-- ---------------------------------------------------------------------
-- H17: Long-running idle in transaction connection
-- Created via a separate sleeper script that opens a TX and sleeps
-- (see scripts/start_idle_tx.sh)
-- ---------------------------------------------------------------------
-- (handled by sleeper script in docker-compose)

-- ---------------------------------------------------------------------
-- H18: event_log has no retention policy and is growing unboundedly
-- This is detected by: large size + oldest_record older than X days
-- + no DELETE/TRUNCATE/partition history
-- ---------------------------------------------------------------------
-- Insert some very old records to demonstrate lack of retention
INSERT INTO event_log (customer_id, event_type, event_data, ip_address, user_agent, created_at)
SELECT
    1 + (random() * 9999)::int,
    'page_view',
    '{}'::jsonb,
    '127.0.0.1'::inet,
    'old-agent',
    NOW() - INTERVAL '2 years' - (random() * 365 || ' days')::interval
FROM generate_series(1, 5000) i;

-- =====================================================================
-- Final analysis (some tables intentionally NOT analyzed for H10)
-- =====================================================================
ANALYZE orders;
ANALYZE order_items;
ANALYZE event_log;
ANALYZE reviews;
ANALYZE customers;
ANALYZE inventory;
ANALYZE categories;
-- NOTE: products is INTENTIONALLY not analyzed for H10

-- =====================================================================
-- Summary message
-- =====================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TiendaDB v1.0 ready with 18 planted problems';
    RAISE NOTICE 'Master list: /docs/HALLAZGOS_v1.md (instructor only)';
    RAISE NOTICE '========================================';
END $$;

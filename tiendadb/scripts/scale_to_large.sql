-- =====================================================================
-- TiendaDB — Scale to LARGE mode (OPTIONAL)
-- =====================================================================
-- Run this AFTER the base seed has completed if you want a more
-- realistic dataset (~2 GB, 5-10 minutes of seeding).
--
-- Usage:
--   docker exec -i tiendadb psql -U tienda_user -d tiendadb < scripts/scale_to_large.sql
--
-- Targets after scaling:
--   customers      ~500K  (from 10K)
--   products       ~50K   (from 1K)
--   orders         ~3M    (from 100K)
--   order_items    ~9M    (from 300K)
--   reviews        ~1M    (from 30K)
--   event_log      ~5M    (from 200K)
-- =====================================================================

SET client_min_messages = WARNING;

-- =====================================================================
-- Scale customers: 10K -> 500K
-- =====================================================================
INSERT INTO customers (email, full_name, phone, birth_date, city, state, country, loyalty_points, created_at)
SELECT
    'customer_l' || i || '@example.com',
    'Customer Large ' || i || ' Lastname',
    '+52' || (2000000000 + i)::text,
    DATE '1960-01-01' + (random() * 20000)::int,
    (ARRAY['Mexico City', 'Guadalajara', 'Monterrey', 'Queretaro', 'Puebla', 'Tijuana', 'Merida', 'Cancun'])[1 + (i % 8)],
    (ARRAY['CDMX', 'JAL', 'NL', 'QRO', 'PUE', 'BC', 'YUC', 'QROO'])[1 + (i % 8)],
    'MX',
    (random() * 5000)::int,
    NOW() - (random() * 730 || ' days')::interval
FROM generate_series(10001, 500000) i;

-- =====================================================================
-- Scale products: 1K -> 50K
-- =====================================================================
INSERT INTO products (sku, name, description, category_id, price, cost, weight_kg, is_active, created_at)
SELECT
    'SKU-L-' || lpad(i::text, 6, '0'),
    'Product Large ' || i,
    'Detailed product description with various features. ' || repeat('Extra content to make description larger. ', 5),
    1 + (i % 50),
    (random() * 5000 + 50)::numeric(10, 2),
    (random() * 2500 + 25)::numeric(10, 2),
    (random() * 10 + 0.1)::numeric(8, 3),
    CASE WHEN i % 20 = 0 THEN FALSE ELSE TRUE END,
    NOW() - (random() * 1095 || ' days')::interval
FROM generate_series(10001, 50000) i;

-- inventory for new products
INSERT INTO inventory (product_id, quantity, reorder_point, last_restock)
SELECT
    p.id,
    (random() * 500)::int,
    10 + (random() * 50)::int,
    NOW() - (random() * 90 || ' days')::interval
FROM products p
WHERE p.id NOT IN (SELECT product_id FROM inventory WHERE product_id IS NOT NULL);

-- =====================================================================
-- Scale orders: 100K -> 3M (in batches)
-- =====================================================================
DO $$
DECLARE
    batch INTEGER;
BEGIN
    FOR batch IN 1..29 LOOP
        INSERT INTO orders (customer_id, order_date, status, total, shipping_cost, tax, payment_method, shipping_city, shipping_state, created_at)
        SELECT
            1 + (random() * 499999)::int,
            NOW() - (random() * 730 || ' days')::interval,
            CASE WHEN random() < 0.05 THEN (ARRAY['shipped', 'delivered', 'cancelled', 'refunded'])[1 + (random() * 3)::int]
                 ELSE 'pending' END,
            (random() * 10000 + 100)::numeric(12, 2),
            (random() * 200)::numeric(8, 2),
            (random() * 1600)::numeric(8, 2),
            (ARRAY['credit_card', 'debit_card', 'paypal', 'cash', 'transfer'])[1 + (random() * 4)::int],
            (ARRAY['Mexico City', 'Guadalajara', 'Monterrey', 'Queretaro', 'Puebla'])[1 + (random() * 4)::int],
            (ARRAY['CDMX', 'JAL', 'NL', 'QRO', 'PUE'])[1 + (random() * 4)::int],
            NOW() - (random() * 730 || ' days')::interval
        FROM generate_series(1, 100000) i;
        RAISE NOTICE 'Orders batch % done', batch;
    END LOOP;
END $$;

-- =====================================================================
-- Scale order_items (~3 per order)
-- =====================================================================
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount, subtotal)
SELECT
    o.id,
    1 + (random() * 49999)::int,
    1 + (random() * 5)::int,
    (random() * 1000 + 50)::numeric(10, 2),
    (random() * 50)::numeric(8, 2),
    (random() * 5000 + 50)::numeric(10, 2)
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
WHERE oi.id IS NULL
CROSS JOIN LATERAL generate_series(1, 1 + (random() * 4)::int) gs;

-- =====================================================================
-- Scale reviews: 30K -> 1M
-- =====================================================================
INSERT INTO reviews (product_id, customer_id, rating, comment, is_verified, created_at)
SELECT
    1 + (random() * 49999)::int,
    1 + (random() * 499999)::int,
    1 + (random() * 4)::int,
    'Review comment number ' || i,
    random() < 0.7,
    NOW() - (random() * 730 || ' days')::interval
FROM generate_series(1, 970000) i;

-- =====================================================================
-- Scale event_log: 200K -> 5M (in batches)
-- =====================================================================
DO $$
DECLARE
    batch INTEGER;
BEGIN
    FOR batch IN 1..48 LOOP
        INSERT INTO event_log (customer_id, event_type, event_data, ip_address, user_agent, created_at)
        SELECT
            CASE WHEN random() < 0.8 THEN 1 + (random() * 499999)::int ELSE NULL END,
            (ARRAY['login', 'logout', 'page_view', 'add_to_cart', 'checkout', 'search', 'product_view'])[1 + (random() * 6)::int],
            jsonb_build_object('session_id', md5(random()::text), 'page', '/page/' || (random() * 100)::int),
            ('192.168.' || (random() * 255)::int || '.' || (random() * 255)::int)::inet,
            'Mozilla/5.0 (compatible; demo agent)',
            NOW() - (random() * 90 || ' days')::interval
        FROM generate_series(1, 100000) i;
        RAISE NOTICE 'event_log batch % done', batch;
    END LOOP;
END $$;

-- =====================================================================
-- Re-analyze (except products to keep H10 stale stats)
-- =====================================================================
ANALYZE customers;
ANALYZE inventory;
ANALYZE orders;
ANALYZE order_items;
ANALYZE reviews;
ANALYZE event_log;
ANALYZE categories;

DO $$
BEGIN
    RAISE NOTICE 'TiendaDB scaled to LARGE mode. Planted problems still active.';
END $$;

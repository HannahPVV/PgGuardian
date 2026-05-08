-- =====================================================================
-- TiendaDB v1.0 — Seed data (BASE mode)
-- ~150 MB, levanta en ~1-2 min en laptop modesta
-- For LARGE mode, see scripts/scale_to_large.sql
-- =====================================================================

-- Mute notices for cleaner output
SET client_min_messages = WARNING;

-- =====================================================================
-- categories: 50 categories with hierarchy
-- =====================================================================
INSERT INTO categories (name, parent_id)
SELECT
    CASE (i % 10)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Home'
        WHEN 3 THEN 'Books'
        WHEN 4 THEN 'Sports'
        WHEN 5 THEN 'Toys'
        WHEN 6 THEN 'Beauty'
        WHEN 7 THEN 'Food'
        WHEN 8 THEN 'Garden'
        WHEN 9 THEN 'Auto'
    END || ' - Subcat ' || i,
    CASE WHEN i > 10 THEN ((i % 10) + 1) ELSE NULL END
FROM generate_series(1, 50) i;

-- =====================================================================
-- customers: 10K customers
-- =====================================================================
INSERT INTO customers (email, full_name, phone, birth_date, city, state, country, loyalty_points, created_at)
SELECT
    'customer' || i || '@example.com',
    'Customer ' || i || ' Lastname',
    '+52' || (1000000000 + i)::text,
    DATE '1960-01-01' + (random() * 20000)::int,
    (ARRAY['Mexico City', 'Guadalajara', 'Monterrey', 'Queretaro', 'Puebla', 'Tijuana', 'Merida', 'Cancun'])[1 + (i % 8)],
    (ARRAY['CDMX', 'JAL', 'NL', 'QRO', 'PUE', 'BC', 'YUC', 'QROO'])[1 + (i % 8)],
    'MX',
    (random() * 5000)::int,
    NOW() - (random() * 730 || ' days')::interval
FROM generate_series(1, 10000) i;

-- =====================================================================
-- products: 1K products
-- =====================================================================
INSERT INTO products (sku, name, description, category_id, price, cost, weight_kg, is_active, created_at)
SELECT
    'SKU-' || lpad(i::text, 6, '0'),
    'Product ' || i || ' - ' || (ARRAY['Premium', 'Standard', 'Economy', 'Deluxe', 'Basic'])[1 + (i % 5)],
    'High quality product number ' || i || '. ' ||
    repeat('This is a detailed product description with various features and specifications. ', 3) ||
    CASE WHEN i % 50 = 0 THEN 'SPECIAL EDITION ITEM' ELSE '' END,
    1 + (i % 50),
    (random() * 5000 + 50)::numeric(10, 2),
    (random() * 2500 + 25)::numeric(10, 2),
    (random() * 10 + 0.1)::numeric(8, 3),
    CASE WHEN i % 20 = 0 THEN FALSE ELSE TRUE END,
    NOW() - (random() * 1095 || ' days')::interval
FROM generate_series(1, 1000) i;

-- =====================================================================
-- inventory: one row per product
-- =====================================================================
INSERT INTO inventory (product_id, quantity, reorder_point, last_restock)
SELECT
    p.id,
    (random() * 500)::int,
    10 + (random() * 50)::int,
    NOW() - (random() * 90 || ' days')::interval
FROM products p;

-- =====================================================================
-- orders: 100K orders (the big transactional table)
-- =====================================================================
INSERT INTO orders (customer_id, order_date, status, total, shipping_cost, tax, payment_method, shipping_city, shipping_state, created_at)
SELECT
    1 + (random() * 9999)::int,
    NOW() - (random() * 730 || ' days')::interval,
    -- 95% pending, 5% other (sets up H04 partial index opportunity)
    CASE
        WHEN random() < 0.05 THEN (ARRAY['shipped', 'delivered', 'cancelled', 'refunded'])[1 + (random() * 3)::int]
        ELSE 'pending'
    END,
    (random() * 10000 + 100)::numeric(12, 2),
    (random() * 200)::numeric(8, 2),
    (random() * 1600)::numeric(8, 2),
    (ARRAY['credit_card', 'debit_card', 'paypal', 'cash', 'transfer'])[1 + (random() * 4)::int],
    (ARRAY['Mexico City', 'Guadalajara', 'Monterrey', 'Queretaro', 'Puebla'])[1 + (random() * 4)::int],
    (ARRAY['CDMX', 'JAL', 'NL', 'QRO', 'PUE'])[1 + (random() * 4)::int],
    NOW() - (random() * 730 || ' days')::interval
FROM generate_series(1, 100000) i;

-- =====================================================================
-- order_items: ~3 items per order = 300K rows
-- =====================================================================
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount, subtotal)
SELECT
    o.id,
    1 + (random() * 999)::int,
    1 + (random() * 5)::int,
    (random() * 1000 + 50)::numeric(10, 2),
    (random() * 50)::numeric(8, 2),
    (random() * 5000 + 50)::numeric(10, 2)
FROM orders o
CROSS JOIN LATERAL generate_series(1, 1 + (random() * 4)::int) gs;

-- =====================================================================
-- reviews: 30K reviews
-- =====================================================================
INSERT INTO reviews (product_id, customer_id, rating, comment, is_verified, created_at)
SELECT
    1 + (random() * 999)::int,
    1 + (random() * 9999)::int,
    1 + (random() * 4)::int,
    (ARRAY[
        'Great product, highly recommended.',
        'Not what I expected, average quality.',
        'Excellent value for money.',
        'Arrived damaged, customer service was helpful.',
        'Will buy again, very satisfied.',
        'Average product, nothing special.',
        'Outstanding quality and fast shipping.'
    ])[1 + (random() * 6)::int],
    random() < 0.7,
    NOW() - (random() * 730 || ' days')::interval
FROM generate_series(1, 30000) i;

-- =====================================================================
-- event_log: 200K events
-- =====================================================================
INSERT INTO event_log (customer_id, event_type, event_data, ip_address, user_agent, created_at)
SELECT
    CASE WHEN random() < 0.8 THEN 1 + (random() * 9999)::int ELSE NULL END,
    (ARRAY['login', 'logout', 'page_view', 'add_to_cart', 'checkout', 'search', 'product_view'])[1 + (random() * 6)::int],
    jsonb_build_object('session_id', md5(random()::text), 'page', '/page/' || (random() * 100)::int),
    ('192.168.' || (random() * 255)::int || '.' || (random() * 255)::int)::inet,
    'Mozilla/5.0 (compatible; demo agent)',
    NOW() - (random() * 90 || ' days')::interval
FROM generate_series(1, 200000) i;

-- =====================================================================
-- Update table stats
-- =====================================================================
ANALYZE categories;
ANALYZE customers;
ANALYZE products;
ANALYZE inventory;
ANALYZE orders;
ANALYZE order_items;
ANALYZE reviews;
ANALYZE event_log;

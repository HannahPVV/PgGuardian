#!/bin/bash
# =====================================================================
# H17: Create a long-running idle-in-transaction connection
# This script opens a transaction, runs a query, then sleeps forever.
# =====================================================================

# Wait extra time so the seed scripts finish
sleep 60

# Open a transaction and keep it idle
PGPASSWORD=tienda_pass psql -h db -U tienda_user -d tiendadb <<EOF &
BEGIN;
SELECT pg_sleep(1);
SELECT count(*) FROM customers WHERE country = 'MX';
-- Now stay idle in transaction forever
SELECT pg_sleep(86400);
EOF

# Keep the script running so docker doesn't exit the container
tail -f /dev/null

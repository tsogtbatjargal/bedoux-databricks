-- Track 4 SQL-modernization fixtures (DuckDB). Synthetic, hand-written to hit
-- edge cases: NULL status and amount, trailing spaces, timestamp ties, an order
-- without payment, a customer without orders.
CREATE TABLE customers (customer_id INTEGER, name VARCHAR, region VARCHAR, created_at TIMESTAMP);
INSERT INTO customers VALUES
  (1, 'Ana ', 'west', '2026-10-01 09:00:00'),
  (2, 'Bo Chen', 'east', '2026-10-03 10:30:00'),
  (3, 'Cy', NULL, '2026-10-05 08:15:00'),
  (4, 'Dee Ray', 'west', '2026-10-07 17:45:00'),
  (5, 'Eli', 'north', '2026-10-09 12:00:00');

CREATE TABLE orders (order_id INTEGER, customer_id INTEGER, status VARCHAR, order_date DATE, updated_at TIMESTAMP);
INSERT INTO orders VALUES
  (101, 1, 'paid',      '2026-11-01', '2026-11-01 10:00:00'),
  (102, 1, 'shipped',   '2026-11-02', '2026-11-03 02:00:00'),
  (103, 2, 'placed',    '2026-11-02', '2026-11-02 11:20:00'),
  (104, 2, NULL,        '2026-11-03', '2026-11-03 02:00:00'),
  (105, 3, 'cancelled', '2026-11-03', '2026-11-03 09:10:00'),
  (106, 4, 'paid',      '2026-11-03', '2026-11-03 02:00:00'),
  (107, 4, 'shipped',   '2026-11-04', '2026-11-04 15:00:00'),
  (108, 1, 'paid',      '2026-11-04', '2026-11-04 18:30:00'),
  (109, 3, 'placed',    '2026-11-05', '2026-11-05 07:45:00'),
  (110, 2, 'paid',      '2026-11-05', '2026-11-05 20:00:00');

CREATE TABLE order_lines (order_id INTEGER, line_no INTEGER, product_id INTEGER, quantity INTEGER, unit_price DECIMAL(10,2));
INSERT INTO order_lines VALUES
  (101, 1, 1, 2, 4.50), (101, 2, 4, 1, 19.99),
  (102, 1, 6, 3, 45.00),
  (103, 1, 2, 5, 12.00), (103, 2, 9, 1, 2.75),
  (104, 1, 3, 4, 7.25),
  (105, 1, 5, 1, 3.10),
  (106, 1, 8, 2, 15.50), (106, 2, 10, 1, 29.90), (106, 3, 1, 7, 4.50),
  (107, 1, 11, 3, 11.40),
  (108, 1, 6, 1, 45.00), (108, 2, 12, 2, 6.60),
  (109, 1, 7, 1, 8.80),
  (110, 1, 4, 3, 19.99), (110, 2, 2, 1, 12.00);

CREATE TABLE payments (payment_id INTEGER, order_id INTEGER, amount DECIMAL(10,2), settled_date DATE);
INSERT INTO payments VALUES
  (1, 101, 28.99, '2026-11-01'),
  (2, 102, 135.00, '2026-11-02'),
  (3, 106, 92.40, '2026-11-04'),
  (4, 107, 34.20, '2026-11-04'),
  (5, 108, 58.20, '2026-11-05'),
  (6, 110, 71.97, '2026-11-06'),
  (7, 110, NULL, NULL),
  (8, 999, 10.00, '2026-11-06');

-- Fix: purchase_order_code_key was incorrectly applied to "name" instead of "code"
ALTER TABLE reference_core.purchase_order
    DROP CONSTRAINT IF EXISTS purchase_order_code_key;

ALTER TABLE reference_core.purchase_order
    ADD CONSTRAINT purchase_order_code_key UNIQUE (code);

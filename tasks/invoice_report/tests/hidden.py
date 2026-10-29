import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from invoices import parse_amount, invoice_total
import invoices as _m

raw = ["19.99", "5.50", "100.00"]
amounts = [parse_amount(r) for r in raw]
assert invoice_total(amounts) == 125.49, invoice_total(amounts)
assert parse_amount("19.99") == 19.99, parse_amount("19.99")
print("ALL TESTS PASSED")

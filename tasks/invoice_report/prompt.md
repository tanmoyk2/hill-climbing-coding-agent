Invoice totals come out short.

`invoice_total(amounts)` in `src/invoices/report.py` adds up the line amounts, but a $19.99 line and a $5.50 line total $24.00 instead of $25.49 -- the cents are being lost. Please fix the root cause so totals are exact.

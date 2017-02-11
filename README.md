Syncs Stripe transactions with Xero.

Copy `config.json.sample` to `config.json` and customize.

Run with `python sync.py YYYY-MM-DD` where YYYY-MM-DD represents the date you'd like to start importing transactions.
Transactions are only imported for full days, and fees are rolled up daily.

Outputs to `out.csv`

Tracking categories actually get put in the Description line, since Xero doesn't seem to actually do anything with it
when it's imported as the actual Tracking field.

import stripe
import json
import logging
import csv
from datetime import date, datetime
import calendar
import itertools
import operator
import sys
from unidecode import unidecode

logging.basicConfig(level=logging.INFO)

class StripeTransactionSync:
    def __init__(self):
        # Load config
        with open('config.json') as config_file:
            self.config = json.load(config_file)

        stripe.api_key = self.config['stripe_secret']

    def _fetchTransactionsAfter(self, time):
        txns = []
        last = None
        last_night = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        while True:
            response = stripe.BalanceTransaction.all(
                limit=100,
                expand=['data.source'],
                created={'gte': time, 'lt': calendar.timegm(last_night.timetuple())},
                starting_after=last
            )

            txns.extend(response.data)
            
            if response.has_more:
                last=response.data[-1].id
            else:
                break

        return txns

    def _mapTransaction(self, txn, field):
        try:
            if field in self.config['mappings']:
                val = self.config['mappings'][field]
                if isinstance(val, dict):
                    if not('source' in txn and 'metadata' in txn.source and val['key'] in txn.source.metadata):
                        return None
                    index = txn.source.metadata[val['key']]
                    return val['values'][index] if (index in val['values']) else  None
                else:
                    return val
            else:
                return None
        except:
            return None

    def _formatTransaction(self, txn):
        tracking = self._mapTransaction(txn, 'tracking');
        description = unidecode(txn.description) if txn.description else None

        if tracking and description:
            xero_description = "{} - {}".format(tracking, description)
        elif tracking:
            xero_description = tracking
        elif description:
            xero_description = description
        else:
            xero_description = None

        return {
            'reference': txn.id,
            'description': xero_description,
            'amount': float(txn.amount)/100,
            'created': date.fromtimestamp(txn.created).isoformat(),
            'payee': 'CodeDay Attendee' if tracking else None
        }

    def _rollupFees(self, txns):
        days = itertools.groupby(txns, key=lambda txn: date.fromtimestamp(txn.created).isoformat())
        return [{
                'reference': 'Stripe fees for {}'.format(k),
                'description': 'Stripe fees for {}'.format(k),
                'payee': 'Stripe',
                'amount': float(sum(i['fee'] for i in v))/-100,
                'created': k
            } for k, v in days]

    def _getTransactionsAndFeesAfter(self, after):
        txns = self._fetchTransactionsAfter(after)
        result = [self._formatTransaction(txn) for txn in txns]
        result.extend(self._rollupFees(txns))
        result.sort(key=operator.itemgetter('created'))
        return result

# 5 Dec 2015

txn_start = datetime.strptime(sys.argv[1], '%Y-%m-%d')

s = StripeTransactionSync()
txns = s._getTransactionsAndFeesAfter(calendar.timegm(txn_start.timetuple()))
with open('out.csv', 'w') as csv_file:
    headings = ['created','amount','payee','description','reference']
    writer = csv.DictWriter(csv_file, fieldnames=headings)

    writer.writeheader()
    for txn in txns:
        writer.writerow(txn)

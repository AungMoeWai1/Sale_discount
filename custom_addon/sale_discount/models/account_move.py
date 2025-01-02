from contextlib import nullcontext
from odoo import models, fields, api, Command

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _sync_tax_lines(self, tax_container):

        res = super()._sync_tax_lines(tax_container)

        # if not tax_container:
        #     return res
        #
        # if 'discount_fixed' in tax_container:
        #     discount_value = tax_container['discount_fixed']
        #     for line in tax_container.get('lines', []):
        #         if line.get('tax_id'):
        #             # Adjust discount and tax base
        #             line['discount_amount'] = discount_value
        #             line['tax_base'] = line['price_unit'] - discount_value
        #             # Ensure deferred_start_date is set
        #         line['deferred_start_date'] = line.get('deferred_start_date', None)
        return res

    def action_post(self):
        """Override to update payment state."""
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.state == 'posted':
                # Recompute amount_due based on move lines
                move.amount_residual = sum(line.price_total for line in move.invoice_line_ids)
                move.payment_state = 'not_paid' if move.amount_residual > 0 else 'paid'
        return res

import logging

from odoo import api, fields, models, Command, _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_fixed = fields.Float(
        string="Fixed Discount",
        digits="Product Price",
        default=0.0,
        help="Fixed amount discount for this line.",
    )

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id', 'discount_fixed')
    def _compute_totals(self):
        """Extend computation to includ_compute_discount_percentagee `discount_fixed`."""
        res=super(AccountMoveLine, self)._compute_totals()
        AccountTax = self.env['account.tax']
        for line in self:
            # Skip computation for non-product lines
            if line.display_type not in ('product', 'cogs'):
                line.price_total = line.price_subtotal = False
                continue

            # Prepare the base line for tax computation
            base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)

            # Adjust the base line to reflect fixed discount if available
            if line.discount_fixed > 0:
                base_line['price_unit'] -= line.discount_fixed / line.quantity

            # Add tax details in the base line
            AccountTax._add_tax_details_in_base_line(base_line, line.company_id)

            # Compute the price_subtotal and price_totalr
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']

            # Ensure journal items for debit/credit are calculated correctly
            # Update debit and credit based on price_total
            if line.account_id.account_type == 'receivable':
                line.debit = line.price_total
                line.credit = 0.0
            elif line.account_id.account_type == 'payable':
                line.debit = 0.0
                line.credit = line.price_total
        return res

    # def _compute_amount_residual(self):
    #     res=super(AccountMoveLine, self)._compute_amount_residual()
    #     """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
    #         This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
    #         for unreconciled lines, and something in-between for partially reconciled lines.
    #     """
    #     need_residual_lines = self.filtered(lambda x: x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card'))
    #     # Run the residual amount computation on all lines stored in the db. By
    #     # using _origin, new records (with a NewId) are excluded and the
    #     # computation works automagically for virtual onchange records as well.
    #     stored_lines = need_residual_lines._origin
    #
    #     if stored_lines:
    #         self.env['account.partial.reconcile'].flush_model()
    #         self.env['res.currency'].flush_model(['decimal_places'])
    #
    #         aml_ids = tuple(stored_lines.ids)
    #         self._cr.execute('''
    #             SELECT
    #                 part.debit_move_id AS line_id,
    #                 'debit' AS flag,
    #                 COALESCE(SUM(part.amount), 0.0) AS amount,
    #                 ROUND(SUM(part.debit_amount_currency), curr.decimal_places) AS amount_currency
    #             FROM account_partial_reconcile part
    #             JOIN res_currency curr ON curr.id = part.debit_currency_id
    #             WHERE part.debit_move_id IN %s
    #             GROUP BY part.debit_move_id, curr.decimal_places
    #             UNION ALL
    #             SELECT
    #                 part.credit_move_id AS line_id,
    #                 'credit' AS flag,
    #                 COALESCE(SUM(part.amount), 0.0) AS amount,
    #                 ROUND(SUM(part.credit_amount_currency), curr.decimal_places) AS amount_currency
    #             FROM account_partial_reconcile part
    #             JOIN res_currency curr ON curr.id = part.credit_currency_id
    #             WHERE part.credit_move_id IN %s
    #             GROUP BY part.credit_move_id, curr.decimal_places
    #         ''', [aml_ids, aml_ids])
    #         amounts_map = {
    #             (line_id, flag): (amount, amount_currency)
    #             for line_id, flag, amount, amount_currency in self.env.cr.fetchall()
    #         }
    #     else:
    #         amounts_map = {}
    #
    #     # Lines that can't be reconciled with anything since the account doesn't allow that.
    #     for line in self - need_residual_lines:
    #         line.amount_residual = 0.0
    #         line.amount_residual_currency = 0.0
    #         line.reconciled = False
    #
    #     for line in need_residual_lines:
    #         # Since this part could be call on 'new' records, 'company_currency_id'/'currency_id' could be not set.
    #         comp_curr = line.company_currency_id or self.env.company.currency_id
    #         foreign_curr = line.currency_id or comp_curr
    #
    #         # Retrieve the amounts in both foreign/company currencies. If the record is 'new', the amounts_map is empty.
    #         debit_amount, debit_amount_currency = amounts_map.get((line._origin.id, 'debit'), (0.0, 0.0))
    #         credit_amount, credit_amount_currency = amounts_map.get((line._origin.id, 'credit'), (0.0, 0.0))
    #
    #         # Subtract the values from the account.partial.reconcile to compute the residual amounts.
    #         line.amount_residual = comp_curr.round(line.balance - debit_amount + credit_amount)
    #         line.amount_residual_currency = foreign_curr.round(line.amount_currency - debit_amount_currency + credit_amount_currency)
    #         line.reconciled = (
    #             comp_curr.is_zero(line.amount_residual)
    #             and foreign_curr.is_zero(line.amount_residual_currency)
    #         )

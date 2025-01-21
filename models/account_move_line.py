import logging

from odoo import api, fields, models, Command, _

from odoo.tools import frozendict

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
        """Extend computation to include `discount_fixed`."""
        super(AccountMoveLine,self)._compute_totals()
        AccountTax = self.env['account.tax']
        for line in self:
            # Skip computation for non-product lines
            if line.display_type not in ('product', 'cogs'):
                line.price_total = line.price_subtotal = False
                continue

            # Prepare the base line for tax computation
            base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)

            # Add tax details in the base line
            AccountTax._add_tax_details_in_base_line(base_line, line.company_id)

            # Compute the price_subtotal and price_total
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']

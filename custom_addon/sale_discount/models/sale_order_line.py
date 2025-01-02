from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_fixed = fields.Float(
        string="Discount (Fixed)",
        digits="Product Price",
        help="Fixed amount discount applied per line.",
    )

    @api.depends('discount_fixed', 'discount', 'price_unit', 'product_uom_qty', 'tax_id')
    def _compute_amount(self):
        # Call the parent method to get the standard calculations
        res = super(SaleOrderLine, self)._compute_amount()

        for line in self:

            # Calculate the total price for the line (before discounts)
            total_price = line.price_unit * line.product_uom_qty
            # Validate that the fixed discount does not exceed the total line price
            if line.discount_fixed > total_price:
                raise ValidationError(_("The fixed discount cannot be greater than the total price for the line."))
            # Apply the fixed discount
            adjusted_price = total_price - line.discount_fixed
            # Ensure the adjusted price is not negative
            if adjusted_price < 0:
                raise ValidationError(_("The fixed discount cannot be greater than the total price for the line."))

            # Prepare the base line for tax computation (after applying the fixed discount)
            base_line = line._prepare_base_line_for_taxes_computation()

            # Apply tax details to the base line
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)

            # Now calculate the price_subtotal, price_total, and price_tax
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

        return res

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({
            'discount_fixed': self.discount_fixed,
            'price_unit': self.price_unit,
            'quantity': self.product_uom_qty,
        })
        return res


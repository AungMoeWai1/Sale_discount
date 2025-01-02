from odoo import api, fields, models,_

from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount_fixed = fields.Float(string="Discount Amount", digits="Product Price", default=0.000)

    @api.depends('discount_fixed', 'discount', 'price_unit', 'product_uom_qty', 'taxes_id')
    def _compute_amount(self):
        # Call the parent method to get the standard calculations
        # res = super(PurchaseOrderLine, self)._compute_amount()

        for line in self:

            # Calculate the total price for the line (before discounts)
            total_price = line.price_unit * line.product_uom_qty

            # Validate that the fixed discount does not exceed the total line price
            if line.discount_fixed > total_price:
                raise ValidationError("The fixed discount cannot be greater than the total price for the line.")

            # Apply the fixed discount
            adjusted_price = total_price - line.discount_fixed

            # Ensure the adjusted price is not negative
            if adjusted_price < 0:
                raise ValidationError("The fixed discount cannot be greater than the total price for the line.")

            base_line = line._prepare_base_line_for_taxes_computation()

            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)

            # Now calculate the price_subtotal, price_total, and price_tax
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

        # return res

    def _prepare_account_move_line(self):
        """Pass fixed discount to the invoice line."""
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        res.update({
            "discount_fixed": self.discount_fixed,
        })
        return res

from odoo import api, models

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line.price_total')
    def _compute_amounts(self):
        """Compute the totals for the order."""
        super(PurchaseOrder,self)._compute_amounts()

        for order in self:
            amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            amount_tax = sum(line.price_tax for line in order.order_line)
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

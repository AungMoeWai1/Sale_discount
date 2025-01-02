from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def automate_validate_order(self):
        for order in self:
            # Ensure the sale order is in draft state before proceeding
            if order.state != 'draft':
                raise ValidationError("The sale order must be in the 'Draft' state to confirm and validate.")

            for line in order.order_line:
                product = line.product_id
                require_qty = line.product_uom_qty
                # Get the available stock by checking the stock.quant model
                available_qty = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                ]).quantity

                if available_qty < require_qty:
                    raise ValidationError((
                        f"Not enough stock for {product.display_name}. at {self.env.ref('stock.stock_location_stock').display_name}     "
                        f"Required: {require_qty}, Available: {available_qty}."
                    ))

            # Confirm the sale order
            super(SaleOrder, order).action_confirm()

            # Process delivery order automatically
            for picking in order.picking_ids:
                if picking.state not in ('done', 'cancel'):
                    if picking.state in ('waiting', 'confirmed'):  # Ensure it is ready
                        picking.action_confirm()  # Confirm delivery
                    if picking.state == 'assigned':  # If ready to transfer
                        picking.action_assign()  # Assign stock
                        picking.button_validate()  # Validate picking

            # # Create the invoice automatically
            invoice = order._create_invoices()
            invoice.action_post()  # Post the invoice to validate it

            # Register payment for the invoice
            payment_method = self.env.ref('account.account_payment_method_manual_in')  # Adjust payment method if needed
            journal = self.env['account.journal'].search([('type', '=', 'bank')],
                                                         limit=1)  # Use the first available bank journal
            if not journal:
                raise ValidationError("No bank journal found to register the payment.")

            # Create payment
            payment_vals = {
                'payment_type': 'inbound',
                'payment_method_id': payment_method.id,
                'partner_type': 'customer',
                'partner_id': order.partner_id.id,
                'amount': invoice.amount_total,
                'currency_id': invoice.currency_id.id,
                'journal_id': journal.id,
                'invoice_ids': [(4, invoice.id)],
            }

            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()  # Post the payment to mark it as paid
            # Need to change state to paid

            # Reconcile the payment with the invoice to mark it as paid
            payment_lines = self.env['account.move.line'].search([
                ('move_id', '=', payment.move_id.id),
                ('account_id', '=', order.partner_id.property_account_receivable_id.id)
            ])

            invoice_lines = self.env['account.move.line'].search([
                ('move_id', '=', invoice.id),
                ('account_id', '=', order.partner_id.property_account_receivable_id.id)
            ])

            # Reconcile the lines
            payment_lines |= invoice_lines
            payment_lines.reconcile()

            payment.action_validate()  # validate in payment

        return True

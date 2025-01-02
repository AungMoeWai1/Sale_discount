from odoo import models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def create_payment(self, invoice):
        # Create a payment for the invoice
        payment = self.env['account.payment'].create({
            'amount': invoice.amount_total,  # Ensure this is the correct amount
            'payment_type': 'out_invoice' if invoice.move_type == 'out_invoice' else 'in_invoice',
            'partner_id': invoice.partner_id.id,
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'invoice_ids': [(6, 0, [invoice.id])],
        })
        payment.action_post()  # Post the payment
        return payment

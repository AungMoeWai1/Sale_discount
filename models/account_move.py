from odoo import api, fields, models, _
from contextlib import nullcontext


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_quick_edit_suggestions(self):
        """
        Extend the existing method to include custom logic for `discount_fixed`.
        """
        # Call the parent method to retain original functionality
        suggestions = super(AccountMove, self)._get_quick_edit_suggestions()

        if not suggestions or not self.quick_edit_total_amount:
            return suggestions

        # Add custom logic for `discount_fixed`
        discount_fixed = getattr(self, 'discount_fixed', 0.0)  # Safely retrieve `discount_fixed`
        if discount_fixed:
            # Adjust the remaining amount by subtracting `discount_fixed`
            remaining_amount = self.quick_edit_total_amount - discount_fixed
            # Retrieve the taxes
            taxes = self.env['account.tax'].browse(suggestions['tax_ids'])

            # Recompute the untaxed price considering `discount_fixed`
            if taxes:
                price_untaxed = taxes.with_context(force_price_include=True).compute_all(remaining_amount)[
                    'total_excluded']
            else:
                price_untaxed = remaining_amount  # No taxes, use remaining amount directly

            # Update the price_unit in the suggestions
            suggestions['price_unit'] = price_untaxed

        return suggestions

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        """
        Extend the base line preparation method to include custom logic for `discount_fixed`.

        :param product_line: An account.move.line.
        :return: A base line prepared for taxes computation.
        """
        self.ensure_one()
        # Call the parent method to retain the original functionality
        base_line = super(AccountMove, self)._prepare_product_base_line_for_taxes_computation(product_line)

        is_invoice = self.is_invoice(include_receipts=True)
        if is_invoice:
            # Custom logic to adjust the price unit with `discount_fixed`
            discount_fixed = getattr(product_line, 'discount_fixed', 0.0)
            if discount_fixed:
                # Recalculate price_unit based on discount_fixed
                adjusted_price_unit = max(product_line.price_unit, 0.0)
                base_line['price_unit'] = adjusted_price_unit

        return base_line

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        """
        Override to include `discount_fixed` handling while calling and extending the parent implementation.
        """
        # Call the parent method
        base_lines, tax_lines = super(AccountMove,self)._get_rounded_base_and_tax_lines(round_from_tax_lines=round_from_tax_lines)

        # Modify base lines to incorporate `discount_fixed`
        for base_line in base_lines:
            related_line = base_line.get('related_line')  # Assuming the parent attaches the line here
            if related_line and hasattr(related_line, 'discount_fixed') and related_line.discount_fixed > 0:
                # Calculate fixed discount per unit
                fixed_discount_per_unit = related_line.discount_fixed / related_line.quantity if related_line.quantity else 0.0

                # Adjust price_unit to account for fixed discount
                base_line['price_unit'] -= fixed_discount_per_unit

        return base_lines, tax_lines

    def _prepare_epd_base_lines_for_taxes_computation_from_base_lines(self, base_lines):
        """
        Override to include handling for 'discount_fixed' in the computation of epd lines.
        """
        # Call the parent method to retain its functionality
        epd_lines = super(AccountMove,self)._prepare_epd_base_lines_for_taxes_computation_from_base_lines(base_lines)

        # Apply custom logic for 'discount_fixed'
        for base_line in epd_lines:
            # Assuming the base_line contains a reference to the original line through 'related_line'
            related_line = base_line.get('related_line')  # Adjust key as per your implementation
            if related_line and hasattr(related_line, 'discount_fixed') and related_line.discount_fixed > 0:
                # Deduct the fixed discount from the amount_currency in the epd line
                fixed_discount_total = related_line.discount_fixed
                base_line['price_unit'] -= fixed_discount_total

        return epd_lines

    def _sync_tax_lines(self, tax_container):
        if not tax_container:
            return nullcontext()

        try:
            if 'discount_fixed' in tax_container:
                discount_value = tax_container['discount_fixed']
                for line in tax_container.get('lines', []):
                    if line.get('tax_id'):
                        line['discount_amount'] = discount_value
                        line['tax_base'] = line['price_unit'] - discount_value

            self.env.cr.commit()  # Make sure changes are reflected
            return nullcontext()

        except Exception as e:
            raise

    def _get_quick_edit_suggestions(self):
        suggestions = super(AccountMove,self)._get_quick_edit_suggestions()
        if not suggestions or 'price_unit' not in suggestions:
            return suggestions

        discount_fixed = self.invoice_payment_term_id.discount_fixed if self.invoice_payment_term_id else 0
        if discount_fixed > 0:
            remaining_amount = self.quick_edit_total_amount - self.tax_totals['total_amount_currency']
            adjusted_amount = max(remaining_amount - discount_fixed, 0)

            taxes = self.env['account.tax'].browse(suggestions['tax_ids'])
            price_untaxed = taxes.with_context(force_price_include=True).compute_all(adjusted_amount)['total_excluded']
            suggestions['price_unit'] = price_untaxed

        return suggestions

    def _get_invoice_counterpart_amls_for_early_payment_discount(self, aml_values_list, open_balance):
        res = super(AccountMove, self)._get_invoice_counterpart_amls_for_early_payment_discount(aml_values_list,
                                                                                                open_balance)

        for aml_values in aml_values_list:
            aml = aml_values['aml']
            invoice = aml.move_id

            fixed_discount = invoice.invoice_payment_term_id.discount_fixed or 0.0
            if fixed_discount > 0:
                for key in ('base_lines', 'tax_lines', 'term_lines'):
                    for grouping_dict, vals in res[key].items():
                        vals['amount_currency'] -= fixed_discount
                        vals['balance'] -= aml.company_currency_id.round(fixed_discount)
                        open_balance -= aml.company_currency_id.round(fixed_discount)

        return res

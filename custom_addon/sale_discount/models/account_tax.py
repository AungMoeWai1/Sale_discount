from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _prepare_tax_base_line_dict(
            self,
            base_line,
            partner=None,
            currency=None,
            product=None,
            taxes=None,
            price_unit=None,
            quantity=None,
            discount=None,
            account=None,
            analytic_distribution=None,
            price_subtotal=None,
            is_refund=False,
            rate=None,
            handle_price_include=True,
            extra_context=None,
    ):
        """Prepare tax base line values and include the fixed discount in the calculation."""
        res = super(AccountTax, self)._prepare_tax_base_line_dict(
            base_line=base_line,
            partner=partner,
            currency=currency,
            product=product,
            taxes=taxes,
            price_unit=price_unit,
            quantity=quantity,
            discount=discount,
            account=account,
            analytic_distribution=analytic_distribution,
            price_subtotal=price_subtotal,
            is_refund=is_refund,
            rate=rate,
            handle_price_include=handle_price_include,
            extra_context=extra_context,
        )

        # Adjust discount if a fixed discount is applied
        # if base_line._name == "account.move.line" and base_line.discount_fixed:
            # discount_amount = base_line.discount_fixed
            # Ensure discount is correctly applied to the subtotal
            # res["discount"] = base_line._compute_discount_percentage()
        if 'discount_fixed' in base_line and base_line['quantity'] > 0:
            base_line['price_unit'] -= base_line['discount_fixed'] / base_line['quantity']
            # Adjust the price_subtotal based on the fixed discount
            # if 'price_subtotal' in res:
                # res['price_subtotal'] -= discount_amount  # Subtract fixed discount from subtotal
                # res['price_total'] = res['price_subtotal']  # Update total to reflect the discount
            taxes_computation_fixed = base_line['tax_ids']._get_tax_details(
                price_unit=base_line['price_unit'],
                quantity=base_line['quantity'],
                precision_rounding=base_line['currency_id'].rounding,
                rounding_method=base_line.get('rounding_method', None),
                product=base_line['product_id'],
                special_mode=base_line['special_mode'],
            )

            base_line['tax_details'] = taxes_computation_fixed
            # return res
        return res

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        """ Convert any representation of a business object ('record') into a base line being a python
        dictionary that will be used to use the generic helpers for the taxes computation.
        """

        def load(field, fallback):
            return self._get_base_line_field_value_from_record(record, field, kwargs, fallback)

        return {
            **kwargs,
            'record': record,
            'id': load('id', 0),

            # Basic fields:
            'product_id': load('product_id', self.env['product.product']),
            'tax_ids': load('tax_ids', self.env['account.tax']),
            'price_unit': load('price_unit', 0.0),
            'quantity': load('quantity', 0.0),
            'discount': load('discount', 0.0),
            'discount_fixed': load('discount_fixed', 0.0),
            'currency_id': load('currency_id', self.env['res.currency']),

            # The special_mode for the taxes computation:
            'special_mode': kwargs.get('special_mode', False),

            'special_type': kwargs.get('special_type', False),

            # Handling the exchange rate if necessary
            'rate': load('rate', 1.0),

            # Accounting settings:
            'sign': load('sign', 1.0),
            'is_refund': load('is_refund', False),
            'tax_tag_invert': load('tax_tag_invert', False),
            'partner_id': load('partner_id', self.env['res.partner']),
            'account_id': load('account_id', self.env['account.account']),
            'analytic_distribution': load('analytic_distribution', None),
        }

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """
        Override to incorporate `discount_fixed` while calling the existing logic.
        """
        res=super()._add_tax_details_in_base_line(base_line,company,rounding_method=None)
        # Handle `discount_fixed` adjustment
        #
        if 'discount' in base_line and base_line.get('quantity',0)>0:
            # Ensure adjusted price_unit reflects the discount
            base_line['price_unit'] *= (1 - (base_line['discount'] / 100.0))
        if 'discount_fixed' in base_line and base_line.get('quantity', 0) > 0:
            # Ensure adjusted price_unit reflects the discount fixed
            base_line['price_unit'] -= (base_line['discount_fixed'] / base_line['quantity'])


        # Recompute tax details based on the adjusted price_unit
        taxes_computation_fixed = base_line['tax_ids']._get_tax_details(
            price_unit=base_line['price_unit'],
            quantity=base_line['quantity'],
            precision_rounding=base_line['currency_id'].rounding,
            rounding_method=rounding_method or company.tax_calculation_rounding_method,
            product=base_line['product_id'],
            special_mode=base_line['special_mode'],
        )

        # Update the tax details for adding tax field in the sale order
        base_line['tax_details'] = taxes_computation_fixed

        rate = base_line['rate']

        tax_details = base_line['tax_details'] = {
            'raw_total_excluded_currency': taxes_computation_fixed['total_excluded'],
            'raw_total_excluded': taxes_computation_fixed['total_excluded'] / rate if rate else 0.0,
            'raw_total_included_currency': taxes_computation_fixed['total_included'],
            'raw_total_included': taxes_computation_fixed['total_included'] / rate if rate else 0.0,
            'taxes_data': [],
        }

        if company.tax_calculation_rounding_method == 'round_per_line':
            tax_details['raw_total_excluded'] = company.currency_id.round(tax_details['raw_total_excluded'])
            tax_details['raw_total_included'] = company.currency_id.round(tax_details['raw_total_included'])
        for tax_data in taxes_computation_fixed['taxes_data']:
            tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
            base_amount = tax_data['base_amount'] / rate if rate else 0.0
            if company.tax_calculation_rounding_method == 'round_per_line':
                tax_amount = company.currency_id.round(tax_amount)
                base_amount = company.currency_id.round(base_amount)
            tax_details['taxes_data'].append({
                **tax_data,
                'raw_tax_amount_currency': tax_data['tax_amount'],
                'raw_tax_amount': tax_amount,
                'raw_base_amount_currency': tax_data['base_amount'],
                'raw_base_amount': base_amount,
            })

        return res


    def _prepare_base_line_grouping_key(self, base_line):
        results = super()._prepare_base_line_grouping_key(base_line)

        # Safely handle the 'deferred_start_date' key
        results['deferred_start_date'] = base_line.get('deferred_start_date', False)

        return results



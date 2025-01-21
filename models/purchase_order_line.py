from odoo import api, fields, models,_

from odoo18.odoo.exceptions import ValidationError


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

        # return res

    def _prepare_account_move_line(self):
        """Pass fixed discount to the invoice line."""
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        res.update({
            "discount_fixed": self.discount_fixed,
        })
        return res
    #
    # @api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id')
    # def _compute_price_unit_and_date_planned_and_name(self):
    #     for line in self:
    #         if not line.product_id or line.invoice_lines or not line.company_id:
    #             continue
    #         params = line._get_select_sellers_params()
    #         seller = line.product_id._select_seller(
    #             partner_id=line.partner_id,
    #             quantity=line.product_qty,
    #             date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
    #             uom_id=line.product_uom,
    #             params=params)
    #
    #         if seller or not line.date_planned:
    #             line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #
    #         # If not seller, use the standard price. It needs a proper currency conversion.
    #         if not seller:
    #             line.discount = 0
    #             unavailable_seller = line.product_id.seller_ids.filtered(
    #                 lambda s: s.partner_id == line.order_id.partner_id)
    #             if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
    #                 # Avoid to modify the price unit if there is no price list for this partner and
    #                 # the line has already one to avoid to override unit price set manually.
    #                 continue
    #             po_line_uom = line.product_uom or line.product_id.uom_po_id
    #             price_unit = line.env['account.tax']._fix_tax_included_price_company(
    #                 line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
    #                 line.product_id.supplier_taxes_id,
    #                 line.taxes_id,
    #                 line.company_id,
    #             )
    #             price_unit = line.product_id.cost_currency_id._convert(
    #                 price_unit,
    #                 line.currency_id,
    #                 line.company_id,
    #                 line.date_order or fields.Date.context_today(line),
    #                 False
    #             )
    #             line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
    #                                                                            self.env[
    #                                                                                'decimal.precision'].precision_get(
    #                                                                                'Product Price')))
    #
    #         elif seller:
    #             price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
    #                                                                                  line.product_id.supplier_taxes_id,
    #                                                                                  line.taxes_id,
    #                                                                                  line.company_id) if seller else 0.0
    #             price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id,
    #                                                      line.date_order or fields.Date.context_today(line), False)
    #             price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
    #                                                                       self.env['decimal.precision'].precision_get(
    #                                                                           'Product Price')))
    #             line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)
    #             line.discount = seller.discount or 0.0
    #
    #         # record product names to avoid resetting custom descriptions
    #         default_names = []
    #         vendors = line.product_id._prepare_sellers({})
    #         product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
    #         default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
    #         for vendor in vendors:
    #             product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
    #             default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
    #         if not line.name or line.name in default_names:
    #             product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
    #             line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

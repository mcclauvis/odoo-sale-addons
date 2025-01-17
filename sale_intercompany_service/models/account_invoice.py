# © 2021 - today Numigi (tm) and all its contributors (https://bit.ly/numigiens)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    interco_service_order_id = fields.Many2one("sale.order", ondelete="restrict")
    interco_customer_invoice_id = fields.Many2one(
        "account.invoice", ondelete="restrict"
    )
    interco_supplier_invoice_id = fields.Many2one(
        "account.invoice", ondelete="restrict"
    )
    is_interco_service = fields.Boolean()
    interco_service_type = fields.Selection(
        [
            ("interco_supplier", "Interco Supplier"),
            ("interco_customer", "Interco Customer"),
            ("customer", "Customer"),
        ],
        compute="_compute_interco_service_type",
        store=True,
    )

    @api.depends("interco_service_order_id", "type", "is_interco_service")
    def _compute_interco_service_type(self):
        for invoice in self:
            if invoice.is_interco_service:
                invoice.interco_service_type = invoice._get_interco_service_type()

    def _get_interco_service_type(self):
        if self.type in ("in_invoice", "in_refund"):
            return "interco_supplier"

        order = self.interco_service_order_id.sudo()
        if order.company_id == self.company_id:
            return "interco_customer"
        else:
            return "customer"

    def open_interco_service_summary(self):
        order = self.sudo().interco_service_order_id
        wizard = self.env["sale.interco.service.invoice"].create(
            {"order_id": order.id, "mode": "summary"}
        )
        action = wizard.get_formview_action()
        action["name"] = _("Interco Service")
        view_ref = (
            "seller_wizard" if self.company_id == order.company_id else "buyer_wizard"
        )
        action["views"] = [
            (self.env.ref(f"sale_intercompany_service.{view_ref}").id, "form")
        ]
        action["target"] = "new"
        return action

    @api.multi
    def action_invoice_open(self):
        for invoice in self.filtered("interco_supplier_invoice_id"):
            invoice._check_amounts_match_supplier_invoice()

        related_interco_invoices = self.sudo().search(
            [("interco_supplier_invoice_id", "in", self.ids)]
        )
        related_interco_invoices._check_amounts_match_supplier_invoice()

        return super().action_invoice_open()

    def _check_amounts_match_supplier_invoice(self):
        supplier_invoice = self.interco_supplier_invoice_id.sudo()
        if float_compare(self.amount_tax, supplier_invoice.amount_tax, 2) != 0:
            raise ValidationError(
                _(
                    "The tax amount ({invoice_amount}) on the invoice ({invoice}) "
                    "does not match the tax amount ({supplier_amount}) on the related "
                    "intercompany supplier invoice ({supplier_invoice}). "
                    "You must adjust the amount of taxes."
                ).format(
                    invoice=self.display_name,
                    invoice_amount=self.amount_tax,
                    supplier_invoice=supplier_invoice.display_name,
                    supplier_amount=supplier_invoice.amount_tax,
                )
            )

        if float_compare(self.amount_total, supplier_invoice.amount_total, 2) != 0:
            raise ValidationError(
                _(
                    "The total amount ({invoice_amount}) on the invoice ({invoice}) "
                    "does not match the total amount ({supplier_amount}) on the related "
                    "intercompany supplier invoice ({supplier_invoice}). "
                    "You must adjust the amounts."
                ).format(
                    invoice=self.display_name,
                    invoice_amount=self.amount_total,
                    supplier_invoice=supplier_invoice.display_name,
                    supplier_amount=supplier_invoice.amount_total,
                )
            )

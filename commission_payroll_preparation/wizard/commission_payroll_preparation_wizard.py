# © 2021 Numigi (tm) and all its contributors (https://bit.ly/numigiens)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CommissionPayrollPreparationWizard(models.TransientModel):
    _name = "commission.payroll.preparation.wizard"
    _description = "Commission Payroll Preparation Wizard"

    target_ids = fields.Many2many(
        "commission.target",
        "commission_payroll_preparation_wizard_target_rel",
        "wizard_id",
        "target_id",
    )
    period = fields.Many2one("payroll.period", required=True)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        defaults["target_ids"] = [(6, 0, self._context.get("active_ids") or [])]
        return defaults

    def confirm(self):
        entries = self._create_payroll_entries()
        return self._make_payroll_entry_action(entries)

    def _create_payroll_entries(self):
        entries = self.env["payroll.preparation.line"]

        for target in self.target_ids:
            if target.state != "confirmed":
                raise ValidationError(_("You generate a payroll entry for a target in a state other than 'confirmed'."))
            elif not target.left_to_generate:
                raise ValidationError(_("There is no amount left to generate a payroll entry for."))
            else:
                entries |= self._create_payroll_entry(target)

        return entries

    def _create_payroll_entry(self, target):
        return self.env["payroll.preparation.line"].create(
            {
                "company_id": target.company_id.id,
                "period_id": self.period.id,
                "employee_id": target.employee_id.id,
                "commission_target_id": target.id,
                "amount": target.left_to_generate,
            }
        )

    def _make_payroll_entry_action(self, entries):
        action = self.env.ref("commission_payroll_preparation.open_payroll_entries").read()[0]
        action["domain"] = [("id", "in", entries.ids)]
        action["context"] = {}
        return action

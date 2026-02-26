from odoo import fields, models
from odoo.tools import SQL


class BudgetReport(models.Model):
    _inherit = 'budget.report'

    def _get_pol_query(self, plan_fnames):
        qty_invoiced_table = SQL("""
            SELECT SUM(
                CASE WHEN COALESCE(uom_aml.id != uom_pol.id, FALSE)
                     THEN ROUND((aml.quantity / uom_aml.factor) * uom_pol.factor, -LOG(uom_pol.rounding)::integer)
                     ELSE COALESCE(aml.quantity, 0)
                END
                * CASE WHEN am.move_type = 'in_invoice' THEN 1
                       WHEN am.move_type = 'in_refund' THEN -1
                       ELSE 0 END
            ) AS qty_invoiced,
            pol.id AS pol_id
            FROM purchase_order po
            LEFT JOIN purchase_order_line pol ON pol.order_id = po.id
            LEFT JOIN account_move_line aml ON aml.purchase_line_id = pol.id
            LEFT JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN uom_uom uom_aml ON uom_aml.id = aml.product_uom_id
            LEFT JOIN uom_uom uom_pol ON uom_pol.id = pol.product_uom
            WHERE aml.parent_state = 'posted'
            GROUP BY pol.id
        """)

        analytic_fields = SQL(
            "CASE WHEN a.key::TEXT = bl.account_id::TEXT "
            "THEN COALESCE(pol.price_subtotal::FLOAT, pol.price_unit * pol.product_qty)"
            "     / COALESCE(NULLIF(pol.product_qty, 0), 1)"
            "     * GREATEST(pol.product_qty - COALESCE(q.qty_invoiced, 0), 0)"
            "     / po.currency_rate"
            "     * (a.value::FLOAT / 100)"
            "     * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END "
            "ELSE 0 END AS account_id"
        )

        condition = SQL("""
                        (a.key::INT = bl.account_id OR a.key::INT IN (
                SELECT id FROM account_analytic_account WHERE id = bl.account_id
            ))
        """)

        return SQL("""
            SELECT 
                (pol.id::TEXT || '-' || a.key) AS id,
                bl.budget_analytic_id AS budget_analytic_id,
                bl.id AS budget_line_id,
                'purchase.order' AS res_model,
                po.id AS res_id,
                po.date_order AS date,
                pol.name AS description,
                pol.company_id AS company_id,
                po.user_id AS user_id,
                'committed' AS line_type,

                0 AS budget,

                -- COMMITTED AMOUNT BY ANALYTIC
                COALESCE(pol.price_subtotal::FLOAT, pol.price_unit * pol.product_qty)
                    / COALESCE(NULLIF(pol.product_qty, 0), 1)
                    * GREATEST(pol.product_qty - COALESCE(q.qty_invoiced, 0), 0)
                    / po.currency_rate
                    * (a.value::FLOAT / 100)
                    * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END AS committed,

                0 AS achieved,

                %(analytic_fields)s

            FROM purchase_order_line pol
            JOIN purchase_order po 
                ON po.id = pol.order_id
               AND po.state IN ('purchase','done')

            -- MULTI-ANALYTIC SPLIT
            CROSS JOIN LATERAL jsonb_each(pol.analytic_distribution) AS a(key, value)

            LEFT JOIN (%(qty_invoiced_table)s) q 
                ON q.pol_id = pol.id

            LEFT JOIN budget_line bl ON
                    (bl.company_id IS NULL OR bl.company_id = po.company_id)
                AND po.date_order >= bl.date_from
                AND date_trunc('day', po.date_order) <= bl.date_to
                AND %(condition)s

            LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id

            WHERE ba.budget_type != 'revenue'
        """,
        qty_invoiced_table=qty_invoiced_table,
        analytic_fields=analytic_fields,
        condition=condition)




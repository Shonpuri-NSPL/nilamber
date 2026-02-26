/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class RFQDashboard extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            requisition_id: this.props.action?.context?.requisition_id || null,
            purchase_ids: [],
            select_type: "",
            project_filter: "",
            projects: [],
        });

        onWillStart(async () => {
            if (!this.state.requisition_id) {
                console.warn("No requisition ID passed.");
                return;
            }
            await this.fetchData();
        });
    }

    async fetchData() {
        const result = await this.orm.call(
            "material.purchase.requisition",
            "get_purchase_line_data",
            [this.state.select_type, this.state.requisition_id, this.state.project_filter]
        );
        this.state.purchase_ids = result || {};
        // Ensure arrays are defined to prevent iteration errors
        this.state.purchase_ids.record_line_ids = this.state.purchase_ids.record_line_ids || [];
        this.state.purchase_ids.partner_ids = this.state.purchase_ids.partner_ids || [];
        this.state.purchase_ids.total = this.state.purchase_ids.total || [];
        // Ensure record_lines are arrays for each record
        (this.state.purchase_ids.record_line_ids || []).forEach(record => {
            record.record_lines = record.record_lines || [];
        });
        // Set projects for filter dropdown
        this.state.projects = this.state.purchase_ids.projects || [];
    }

    onChangeSelectionType(ev) {
        this.state.select_type = ev.target.value;
        this.fetchData();
    }

    onChangeProjectFilter(ev) {
        this.state.project_filter = ev.target.value;
        this.fetchData();
    }

    async onRemoveLine(ev) {
        const id = ev.target.dataset.id;

        await this.orm.call(
            "material.purchase.requisition",
            "remove_line_action",
            [id, this.state.requisition_id]
        );

        await this.fetchData();
    }

    async onConfirmOrder(ev) {
        const purchaseId = ev.target.dataset.id;
        const allIds = this.state.purchase_ids.total.map(po => po.id)


        try {
            await this.orm.call(
                "material.purchase.requisition",
                "confirm_order_action",
                [purchaseId, allIds]
            );

            await this.env.services.action.doAction({
                type: "ir.actions.client",
                tag: "reload",
            });

        } catch (error) {
            const msg =
                error?.data?.message ||
                error?.message ||
                "Unable to confirm Purchase Order";

            this.env.services.notification.add(msg, {
                type: "danger",
                sticky: true,
            });
        }
    }

}

RFQDashboard.template = "material_purchase_requisitions_dashboard.RFQDashboard";

registry.category("actions").add("compare_dashboard", RFQDashboard);

/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * "Back to web app" in the top bar: HR staff who opened an Odoo screen from the SAP B1 web app
 * get back to it in one click (the address is the system parameter grotek_hr.web_app_url).
 */
export class BackToWebApp extends Component {
    static template = "grotek_hr.BackToWebApp";
    static props = {};

    setup() {
        this.state = useState({ url: "" });
        onWillStart(async () => {
            // Framed inside a 2608 tab: the tab strip is the way back, so no button (DT notes 67).
            if (window.self !== window.top) {
                return;
            }
            try {
                const response = await fetch("/grotek_hr/web_app_url", { credentials: "same-origin" });
                this.state.url = response.ok ? (await response.text()).trim() : "";
            } catch {
                this.state.url = "";
            }
        });
    }
}

registry.category("systray").add("grotek_hr.back_to_web_app", { Component: BackToWebApp }, { sequence: 1 });

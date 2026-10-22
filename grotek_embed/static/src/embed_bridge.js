/*
 * Tells the 2608 page that frames Odoo what this Odoo page is doing (DT notes 67, slice 2):
 *   { type: 'grotek-odoo', path, signedOut, dirty }
 * path = where Odoo is (so the 2608 tab reopens there after a reload), signedOut = Odoo's sign-in page is shown,
 * dirty = a form has changes that are not saved. Sent only when the page is framed, and only to the origins in
 * the system parameter grotek_embed.frame_ancestors (read from /grotek_embed/origins); a browser delivers a
 * message only to the origin it is addressed to. Nothing else about the page leaves it.
 */
(function () {
    "use strict";
    if (window.self === window.top) {
        return;
    }
    var origins = null;
    var last = "";

    function state() {
        var path = window.location.pathname + window.location.search;
        return {
            type: "grotek-odoo",
            path: path,
            signedOut: window.location.pathname.indexOf("/web/login") === 0,
            // Odoo shows the Save / Discard buttons of a form only while it has unsaved changes.
            dirty: !!document.querySelector(".o_form_status_indicator_buttons:not(.invisible)"),
        };
    }

    function send() {
        if (!origins) {
            return;
        }
        var s = state();
        var key = JSON.stringify(s);
        if (key === last) {
            return;
        }
        last = key;
        origins.forEach(function (o) {
            try {
                window.parent.postMessage(s, o);
            } catch (e) {
                /* not that origin */
            }
        });
    }

    fetch("/grotek_embed/origins", { credentials: "same-origin" })
        .then(function (r) {
            return r.ok ? r.json() : [];
        })
        .then(function (list) {
            var ancestors = window.location.ancestorOrigins;
            origins = Array.isArray(list) ? list : [];
            if (ancestors && ancestors.length) {
                origins = origins.filter(function (o) {
                    return o === ancestors[0];
                });
            }
            send();
            window.setInterval(send, 1000);
        })
        .catch(function () {
            origins = null;
        });
})();

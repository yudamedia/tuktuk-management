frappe.ui.form.on('Tuktuk Driver', {
    driver_first_name: function (frm) {
        set_driver_name(frm);
    },
    driver_middle_name: function (frm) {
        set_driver_name(frm);
    },
    driver_last_name: function (frm) {
        set_driver_name(frm);
    },
    refresh: function (frm) {
        if (!frm.doc.driver_name) {
            set_driver_name(frm);
        }
    }
});

function set_driver_name(frm) {
    const firstName = frm.doc.driver_first_name || '';
    const middleName = frm.doc.driver_middle_name || '';
    const lastName = frm.doc.driver_last_name || '';
    
    const fullName = [firstName, middleName, lastName].filter(Boolean).join(' ');
    if (!frm.doc.__islocal) {
        frm.set_value('driver_name', fullName);
    }
}

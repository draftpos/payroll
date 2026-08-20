
// Bulletproof background watcher to promote Print button on any report
setInterval(() => {
    if (frappe.get_route()[0] === 'query-report') {
        let page = frappe.pages['query-report'] ? frappe.pages['query-report'].page : null;
        if (page && page.menu && page.inner_toolbar) {
            let menu_print = page.menu.find('[data-label="Print"]');
            let promote_btn = page.inner_toolbar.find('.btn-promote-print');
            
            // If the Print option exists in the 3 dots, but our icon is missing, add it!
            if (menu_print.length > 0 && promote_btn.length === 0) {
                let print_btn = page.add_inner_button(
                    '<svg class="icon icon-sm"><use href="#icon-printer"></use></svg> ' + __('Print'),
                    () => {
                        // Click the original print button inside the menu
                        menu_print.click();
                    }
                );
                print_btn.addClass('btn-promote-print');
                print_btn.attr('title', __('Print'));
                print_btn.css({'margin-right': '10px'});
            }
        }
    }
}, 1000); // Check every 1 second

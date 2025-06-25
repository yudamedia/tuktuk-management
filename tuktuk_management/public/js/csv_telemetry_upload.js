// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/csv_telemetry_upload.js

tuktuk_management.csv_upload = {
    show_upload_dialog: function() {
        const dialog = new frappe.ui.Dialog({
            title: __('Upload Telemetry CSV'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'Attach',
                    fieldname: 'csv_file',
                    label: __('CSV File'),
                    reqd: 1,
                    options: {
                        restrictions: {
                            allowed_file_types: ['.csv']
                        }
                    }
                },
                {
                    fieldtype: 'Select',
                    fieldname: 'mapping_type',
                    label: __('Mapping Type'),
                    options: [
                        '',
                        'auto',
                        'telemetry_export',
                        'battery_update',
                        'location_update',
                        'vehicle_data'
                    ],
                    default: 'auto',
                    description: __('Auto-detect will try to identify the CSV format automatically')
                },
                {
                    fieldtype: 'HTML',
                    fieldname: 'template_download',
                    options: `
                        <div class="mt-3">
                            <h6>CSV Templates:</h6>
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-sm btn-outline-primary" onclick="tuktuk_management.csv_upload.download_template('telemetry_export')">
                                    Telemetry Export
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-primary" onclick="tuktuk_management.csv_upload.download_template('battery_update')">
                                    Battery Update
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-primary" onclick="tuktuk_management.csv_upload.download_template('location_update')">
                                    Location Update
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-primary" onclick="tuktuk_management.csv_upload.download_template('vehicle_data')">
                                    Vehicle Data
                                </button>
                            </div>
                        </div>
                    `
                },
                {
                    fieldtype: 'HTML',
                    fieldname: 'validation_results',
                    options: '<div id="csv-validation-results"></div>'
                }
            ],
            primary_action: function(values) {
                tuktuk_management.csv_upload.process_csv_upload(values, dialog);
            },
            primary_action_label: __('Upload and Process'),
            secondary_action: function(values) {
                if (values.csv_file) {
                    tuktuk_management.csv_upload.validate_csv_file(values.csv_file);
                } else {
                    frappe.msgprint(__('Please select a CSV file first'));
                }
            },
            secondary_action_label: __('Validate CSV')
        });
        
        dialog.show();
        
        // Add file change handler for auto-validation
        dialog.fields_dict.csv_file.$input.on('change', function() {
            const file_url = dialog.get_value('csv_file');
            if (file_url) {
                setTimeout(() => {
                    tuktuk_management.csv_upload.validate_csv_file(file_url);
                }, 500);
            }
        });
        
        return dialog;
    },
    
    validate_csv_file: function(file_url) {
        frappe.show_alert({
            message: __('Validating CSV file...'),
            indicator: 'blue'
        });
        
        // Use the correct method to read file content
        frappe.call({
            method: 'tuktuk_management.api.csv_telemetry.read_file_content',
            args: {
                file_url: file_url
            },
            callback: function(r) {
                if (r.message) {
                    // Validate CSV content
                    frappe.call({
                        method: 'tuktuk_management.api.csv_telemetry.validate_csv_before_upload',
                        args: {
                            csv_content: r.message
                        },
                        callback: function(validation_result) {
                            tuktuk_management.csv_upload.show_validation_results(validation_result.message);
                        }
                    });
                }
            },
            error: function(error) {
                frappe.msgprint({
                    title: __('File Read Error'),
                    message: error.message,
                    indicator: 'red'
                });
            }
        });
    },
    
    show_validation_results: function(validation_data) {
        const results_div = document.getElementById('csv-validation-results');
        
        if (!validation_data.valid) {
            results_div.innerHTML = `
                <div class="alert alert-danger mt-3">
                    <h6><i class="fa fa-exclamation-triangle"></i> Validation Failed</h6>
                    <p><strong>Error:</strong> ${validation_data.error}</p>
                    ${validation_data.headers ? 
                        `<p><strong>Found Headers:</strong> ${validation_data.headers.join(', ')}</p>` : ''}
                </div>
            `;
            return;
        }
        
        const format_info = validation_data.format;
        const processing_time = Math.ceil(validation_data.estimated_processing_time);
        
        results_div.innerHTML = `
            <div class="alert alert-success mt-3">
                <h6><i class="fa fa-check-circle"></i> Validation Successful</h6>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Detected Format:</strong> ${format_info.type.replace('_', ' ').toUpperCase()}</p>
                        <p><strong>Total Rows:</strong> ${validation_data.row_count}</p>
                        <p><strong>Estimated Processing Time:</strong> ~${processing_time} seconds</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Column Mappings:</strong></p>
                        <ul class="small mb-0">
                            ${Object.entries(format_info.mappings).map(([key, index]) => 
                                `<li>${key}: Column ${index + 1} (${validation_data.headers[index]})</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    },
    
    process_csv_upload: function(values, dialog) {
        if (!values.csv_file) {
            frappe.msgprint(__('Please select a CSV file'));
            return;
        }
        
        // Show progress dialog
        const progress_dialog = tuktuk_management.csv_upload.show_progress_dialog();
        
        // Hide main dialog
        dialog.hide();
        
        // Read CSV file content using the correct method
        frappe.call({
            method: 'tuktuk_management.api.csv_telemetry.read_file_content',
            args: {
                file_url: values.csv_file
            },
            callback: function(r) {
                if (r.message) {
                    // Process the CSV
                    frappe.call({
                        method: 'tuktuk_management.api.csv_telemetry.upload_telemetry_csv_data',
                        args: {
                            csv_content: r.message,
                            mapping_type: values.mapping_type || 'auto'
                        },
                        callback: function(result) {
                            progress_dialog.hide();
                            tuktuk_management.csv_upload.show_results_dialog(result.message);
                        },
                        error: function(error) {
                            progress_dialog.hide();
                            frappe.msgprint({
                                title: __('Upload Failed'),
                                message: error.message,
                                indicator: 'red'
                            });
                        }
                    });
                }
            },
            error: function(error) {
                progress_dialog.hide();
                frappe.msgprint({
                    title: __('File Read Error'),
                    message: error.message,
                    indicator: 'red'
                });
            }
        });
    },
    
    show_progress_dialog: function() {
        return new frappe.ui.Dialog({
            title: __('Processing CSV Upload'),
            indicator: 'blue',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'progress_html',
                    options: `
                        <div class="text-center p-4">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="sr-only">Loading...</span>
                            </div>
                            <h5>Processing CSV file...</h5>
                            <p class="text-muted">This may take a few moments depending on file size.</p>
                        </div>
                    `
                }
            ]
        });
    },
    
    show_results_dialog: function(results) {
        const dialog = new frappe.ui.Dialog({
            title: __('CSV Upload Results'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'results_html',
                    options: tuktuk_management.csv_upload.generate_results_html(results)
                }
            ],
            primary_action: function() {
                dialog.hide();
                // Refresh the list view
                if (cur_list) {
                    cur_list.refresh();
                }
            },
            primary_action_label: __('Close')
        });
        
        dialog.show();
    },
    
    generate_results_html: function(results) {
        const success_percentage = results.total_rows > 0 ? 
            Math.round((results.updated / results.total_rows) * 100) : 0;
        
        let html = `
            <div class="csv-upload-results">
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h4 class="text-primary">${results.total_rows}</h4>
                                <small>Total Rows</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h4 class="text-success">${results.updated}</h4>
                                <small>Updated</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h4 class="text-danger">${results.failed}</h4>
                                <small>Failed</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h4 class="text-warning">${results.skipped}</h4>
                                <small>Skipped</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="progress mb-3">
                    <div class="progress-bar bg-success" style="width: ${success_percentage}%">
                        ${success_percentage}% Success
                    </div>
                </div>
        `;
        
        if (results.errors && results.errors.length > 0) {
            html += `
                <div class="mt-4">
                    <h6 class="text-danger">Errors (${results.errors.length}):</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>Row</th>
                                    <th>Error</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            results.errors.slice(0, 10).forEach(error => {
                html += `
                    <tr>
                        <td>${error.row || 'N/A'}</td>
                        <td>${error.message || error}</td>
                    </tr>
                `;
            });
            
            if (results.errors.length > 10) {
                html += `<tr><td colspan="2"><em>... and ${results.errors.length - 10} more errors</em></td></tr>`;
            }
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
        
        if (results.success_details && results.success_details.length > 0) {
            html += `
                <div class="mt-4">
                    <h6 class="text-success">Recent Updates:</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>TukTuk ID</th>
                                    <th>Battery Level</th>
                                    <th>Location</th>
                                    <th>Updated</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            results.success_details.slice(0, 5).forEach(detail => {
                html += `
                    <tr>
                        <td>${detail.tuktuk_id || 'N/A'}</td>
                        <td>${detail.battery_level !== undefined ? flt(detail.battery_level) + '%' : 'N/A'}</td>
                        <td>${detail.location || 'N/A'}</td>
                        <td>${detail.timestamp || 'Now'}</td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        return html;
    },
    
    download_template: function(format_type) {
        frappe.call({
            method: 'tuktuk_management.api.csv_telemetry.get_csv_template',
            args: {
                format_type: format_type
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    const headers = r.message.headers;
                    const csv_content = headers.join(',') + '\n';
                    
                    // Create and download CSV file
                    const blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
                    const link = document.createElement('a');
                    
                    if (link.download !== undefined) {
                        const url = URL.createObjectURL(blob);
                        link.setAttribute('href', url);
                        link.setAttribute('download', `${format_type}_template.csv`);
                        link.style.visibility = 'hidden';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    }
                }
            }
        });
    }
};

// Extend the TukTuk Vehicle list view
const original_onload = frappe.listview_settings['TukTuk Vehicle'] && 
                       frappe.listview_settings['TukTuk Vehicle'].onload || function() {};

frappe.listview_settings['TukTuk Vehicle'].onload = function(listview) {
    // Call original onload if it exists
    original_onload.call(this, listview);
    
    // Add CSV upload button
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
        listview.page.add_action_item(__("CSV Upload"), function() {
            tuktuk_management.csv_upload.show_upload_dialog();
        });
    }
};

// Add CSS for better styling
$(document).ready(function() {
    if (!$('#csv-upload-styles').length) {
        $('head').append(`
            <style id="csv-upload-styles">
                .csv-upload-results .card {
                    margin-bottom: 0.5rem;
                }
                
                .csv-upload-results .card-body {
                    padding: 1rem 0.5rem;
                }
                
                .csv-upload-results .card h4 {
                    margin-bottom: 0.25rem;
                    font-size: 1.5rem;
                }
                
                .csv-upload-results .card small {
                    font-size: 0.75rem;
                    color: #6c757d;
                }
                
                .csv-upload-results .table-responsive {
                    max-height: 300px;
                    overflow-y: auto;
                }
                
                .csv-upload-results .progress {
                    height: 1.5rem;
                }
                
                .csv-upload-results .progress-bar {
                    line-height: 1.5rem;
                    font-weight: bold;
                }
                
                #csv-validation-results .alert {
                    border-left: 4px solid;
                }
                
                #csv-validation-results .alert-success {
                    border-left-color: #28a745;
                }
                
                #csv-validation-results .alert-danger {
                    border-left-color: #dc3545;
                }
            </style>
        `);
    }
});

// Export for global access
window.tuktuk_csv_upload = tuktuk_management.csv_upload;
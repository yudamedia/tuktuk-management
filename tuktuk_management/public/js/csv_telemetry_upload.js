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
                    options: '<div id="csv-template-buttons"></div>'
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
                // Get the file URL properly
                const file_url = dialog.get_value('csv_file');
                console.log('File URL from dialog:', file_url); // Debug log
                
                if (file_url && file_url.trim() !== '') {
                    tuktuk_management.csv_upload.validate_csv_file(file_url);
                } else {
                    // Try to get file URL from the attachment field differently
                    const attach_field = dialog.fields_dict.csv_file;
                    if (attach_field && attach_field.get_value()) {
                        tuktuk_management.csv_upload.validate_csv_file(attach_field.get_value());
                    } else {
                        frappe.msgprint({
                            title: __('No File Selected'),
                            message: __('Please select a CSV file first before validating.'),
                            indicator: 'orange'
                        });
                    }
                }
            },
            secondary_action_label: __('Validate CSV')
        });
        
        dialog.show();
        
        // Add template buttons after dialog is shown
        setTimeout(() => {
            tuktuk_management.csv_upload.add_template_buttons();
        }, 100);
        
        // Add file change handler for auto-validation after file upload completes
        dialog.fields_dict.csv_file.$input.on('change', function() {
            setTimeout(() => {
                const file_url = dialog.get_value('csv_file');
                console.log('File change detected, URL:', file_url); // Debug log
                if (file_url && file_url.trim() !== '') {
                    // Auto-validate after a small delay to ensure file upload is complete
                    setTimeout(() => {
                        tuktuk_management.csv_upload.validate_csv_file(file_url);
                    }, 1000);
                }
            }, 500);
        });
        
        return dialog;
    },
    
    add_template_buttons: function() {
        const container = document.getElementById('csv-template-buttons');
        if (container) {
            container.innerHTML = `
                <div class="mt-3">
                    <h6>CSV Templates:</h6>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" id="template-telemetry">
                            Telemetry Export
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="template-battery">
                            Battery Update
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="template-location">
                            Location Update
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="template-vehicle">
                            Vehicle Data
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listeners
            document.getElementById('template-telemetry').onclick = () => tuktuk_management.csv_upload.download_template('telemetry_export');
            document.getElementById('template-battery').onclick = () => tuktuk_management.csv_upload.download_template('battery_update');
            document.getElementById('template-location').onclick = () => tuktuk_management.csv_upload.download_template('location_update');
            document.getElementById('template-vehicle').onclick = () => tuktuk_management.csv_upload.download_template('vehicle_data');
        }
    },
    
    validate_csv_file: function(file_url) {
        console.log('Validating CSV file with URL:', file_url); // Debug log
        
        if (!file_url || file_url.trim() === '') {
            frappe.msgprint({
                title: __('No File Selected'),
                message: __('Please select a CSV file first before validating.'),
                indicator: 'orange'
            });
            return;
        }
        
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
                console.log('File read response:', r); // Debug log
                if (r.message) {
                    // Validate CSV content
                    frappe.call({
                        method: 'tuktuk_management.api.csv_telemetry.validate_csv_before_upload',
                        args: {
                            csv_content: r.message
                        },
                        callback: function(validation_result) {
                            console.log('Validation result:', validation_result); // Debug log
                            tuktuk_management.csv_upload.show_validation_results(validation_result.message);
                        },
                        error: function(error) {
                            console.error('Validation error:', error); // Debug log
                            frappe.msgprint({
                                title: __('Validation Error'),
                                message: error.message || __('Failed to validate CSV file'),
                                indicator: 'red'
                            });
                        }
                    });
                } else {
                    frappe.msgprint({
                        title: __('File Read Error'),
                        message: __('Could not read the CSV file content. Please try again.'),
                        indicator: 'red'
                    });
                }
            },
            error: function(error) {
                console.error('File read error:', error); // Debug log
                frappe.msgprint({
                    title: __('File Read Error'),
                    message: error.message || __('Failed to read the CSV file'),
                    indicator: 'red'
                });
            }
        });
    },
    
    show_validation_results: function(validation_data) {
        const results_div = document.getElementById('csv-validation-results');
        
        if (!validation_data) {
            results_div.innerHTML = `
                <div class="alert alert-warning mt-3">
                    <h6><i class="fa fa-exclamation-triangle"></i> No Validation Data</h6>
                    <p>Could not get validation results. Please try again.</p>
                </div>
            `;
            return;
        }
        
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
        
        const detected_format = validation_data.detected_format || 'Unknown';
        
        results_div.innerHTML = `
            <div class="alert alert-success mt-3">
                <h6><i class="fa fa-check-circle"></i> Validation Successful</h6>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Detected Format:</strong> ${detected_format.replace('_', ' ').toUpperCase()}</p>
                        <p><strong>Total Rows:</strong> ${validation_data.row_count}</p>
                        <p><strong>Columns:</strong> ${validation_data.headers ? validation_data.headers.length : 'Unknown'}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Sample Headers:</strong></p>
                        <ul class="small mb-0">
                            ${validation_data.headers ? 
                                validation_data.headers.slice(0, 5).map((header, index) => 
                                    `<li>Column ${index + 1}: ${header}</li>`
                                ).join('') : 
                                '<li>No headers detected</li>'
                            }
                            ${validation_data.headers && validation_data.headers.length > 5 ? 
                                `<li>... and ${validation_data.headers.length - 5} more columns</li>` : ''}
                        </ul>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        ✅ CSV file is ready for processing. Click "Upload and Process" to continue.
                    </small>
                </div>
            </div>
        `;
    },
    
    process_csv_upload: function(values, dialog) {
        const file_url = dialog.get_value('csv_file');
        console.log('Processing CSV with URL:', file_url); // Debug log
        
        if (!file_url || file_url.trim() === '') {
            frappe.msgprint({
                title: __('No File Selected'),
                message: __('Please select a CSV file first'),
                indicator: 'orange'
            });
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
                file_url: file_url
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
                            if (result.message) {
                                tuktuk_management.csv_upload.show_results_dialog(result.message);
                            } else {
                                frappe.msgprint({
                                    title: __('Upload Failed'),
                                    message: __('No results returned from CSV processing'),
                                    indicator: 'red'
                                });
                            }
                        },
                        error: function(error) {
                            progress_dialog.hide();
                            frappe.msgprint({
                                title: __('Upload Failed'),
                                message: error.message || __('Failed to process CSV file'),
                                indicator: 'red'
                            });
                        }
                    });
                } else {
                    progress_dialog.hide();
                    frappe.msgprint({
                        title: __('File Read Error'),
                        message: __('Could not read the CSV file content'),
                        indicator: 'red'
                    });
                }
            },
            error: function(error) {
                progress_dialog.hide();
                frappe.msgprint({
                    title: __('File Read Error'),
                    message: error.message || __('Failed to read the CSV file'),
                    indicator: 'red'
                });
            }
        });
    },
    
    show_progress_dialog: function() {
        const progress_dialog = new frappe.ui.Dialog({
            title: __('Processing CSV'),
            size: 'small',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'progress_html',
                    options: `
                        <div class="text-center">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="sr-only">Loading...</span>
                            </div>
                            <p class="text-muted">Processing your CSV file...</p>
                            <p class="small">This may take a few minutes depending on file size.</p>
                        </div>
                    `
                }
            ]
        });
        
        progress_dialog.show();
        progress_dialog.$wrapper.find('.btn-modal-close').hide(); // Hide close button
        
        return progress_dialog;
    },
    
    show_results_dialog: function(results) {
        const success_rate = results.total_rows > 0 ? 
            Math.round((results.updated / results.total_rows) * 100) : 0;
        
        const results_dialog = new frappe.ui.Dialog({
            title: __('CSV Upload Results'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'results_summary',
                    options: `
                        <div class="csv-upload-results">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="card text-center border-primary">
                                        <div class="card-body">
                                            <h4 class="text-primary">${results.total_rows}</h4>
                                            <small>Total Rows</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center border-success">
                                        <div class="card-body">
                                            <h4 class="text-success">${results.updated}</h4>
                                            <small>Updated</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center border-danger">
                                        <div class="card-body">
                                            <h4 class="text-danger">${results.failed}</h4>
                                            <small>Failed</small>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card text-center border-warning">
                                        <div class="card-body">
                                            <h4 class="text-warning">${results.skipped}</h4>
                                            <small>Skipped</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <div class="progress">
                                    <div class="progress-bar bg-success" role="progressbar" 
                                         style="width: ${success_rate}%" 
                                         aria-valuenow="${success_rate}" aria-valuemin="0" aria-valuemax="100">
                                        ${success_rate}% Success Rate
                                    </div>
                                </div>
                            </div>
                            
                            ${results.errors && results.errors.length > 0 ? `
                                <div class="mt-3">
                                    <h6 class="text-danger">Errors:</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm table-striped">
                                            <tbody>
                                                ${results.errors.slice(0, 10).map(error => 
                                                    `<tr><td class="small text-danger">${error}</td></tr>`
                                                ).join('')}
                                                ${results.errors.length > 10 ? 
                                                    `<tr><td class="small text-muted">... and ${results.errors.length - 10} more errors</td></tr>` : ''}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${results.success_details && results.success_details.length > 0 ? `
                                <div class="mt-3">
                                    <h6 class="text-success">Successfully Updated TukTuks:</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm table-striped">
                                            <thead>
                                                <tr>
                                                    <th>TukTuk ID</th>
                                                    <th>Battery Level</th>
                                                    <th>Updated</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${results.success_details.slice(0, 10).map(detail => `
                                                    <tr>
                                                        <td class="small">${detail.tuktuk_id || 'N/A'}</td>
                                                        <td class="small">${detail.battery_level ? detail.battery_level + '%' : 'N/A'}</td>
                                                        <td class="small">${detail.timestamp || 'N/A'}</td>
                                                    </tr>
                                                `).join('')}
                                                ${results.success_details.length > 10 ? 
                                                    `<tr><td colspan="3" class="small text-muted">... and ${results.success_details.length - 10} more updates</td></tr>` : ''}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    `
                }
            ],
            primary_action: function() {
                results_dialog.hide();
                // Refresh the list view
                if (cur_list) {
                    cur_list.refresh();
                }
            },
            primary_action_label: __('Close')
        });
        
        results_dialog.show();
    },
    
    download_template: function(format_type) {
        frappe.call({
            method: 'tuktuk_management.api.csv_telemetry.get_csv_template',
            args: {
                format_type: format_type
            },
            callback: function(r) {
                if (r.message) {
                    const blob = new Blob([r.message.content], { type: 'text/csv' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = r.message.filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    frappe.show_alert({
                        message: __('Template downloaded successfully'),
                        indicator: 'green'
                    });
                }
            }
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
                
                #csv-validation-results .alert-warning {
                    border-left-color: #ffc107;
                }
            </style>
        `);
    }
});

// Export for global access
window.tuktuk_csv_upload = tuktuk_management.csv_upload;
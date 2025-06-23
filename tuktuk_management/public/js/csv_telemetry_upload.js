// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/csv_telemetry_upload.js

// CSV Telemetry Upload Interface
frappe.provide('tuktuk_management.csv_upload');

tuktuk_management.csv_upload = {
    
    show_upload_dialog: function() {
        const dialog = new frappe.ui.Dialog({
            title: __('Upload Telemetry CSV Data'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'upload_info',
                    options: `
                        <div class="alert alert-info">
                            <h6><i class="fa fa-info-circle"></i> CSV Upload Information</h6>
                            <p>Upload CSV files containing telemetry data to update vehicle information in bulk.</p>
                            <ul class="mb-0">
                                <li><strong>Telemetry Export:</strong> Direct export from your telemetry platform</li>
                                <li><strong>Battery Update:</strong> Update battery levels for multiple vehicles</li>
                                <li><strong>Location Update:</strong> Update GPS coordinates for vehicles</li>
                                <li><strong>Vehicle Data:</strong> Complete vehicle information update</li>
                            </ul>
                        </div>
                    `
                },
                {
                    fieldtype: 'Select',
                    fieldname: 'mapping_type',
                    label: __('Vehicle Identification Method'),
                    options: [
                        {label: 'Auto-detect', value: 'auto'},
                        {label: 'By TukTuk ID', value: 'tuktuk_id'},
                        {label: 'By Device ID', value: 'device_id'},
                        {label: 'By IMEI', value: 'imei'}
                    ],
                    default: 'auto',
                    description: 'How to match CSV rows to vehicles'
                },
                {
                    fieldtype: 'Attach',
                    fieldname: 'csv_file',
                    label: __('CSV File'),
                    reqd: 1,
                    description: 'Select your CSV file containing telemetry data'
                },
                {
                    fieldtype: 'HTML',
                    fieldname: 'template_section',
                    options: `
                        <div class="mt-3">
                            <h6>Download Templates:</h6>
                            <div class="btn-group" role="group">
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
        
        // Read file content
        frappe.call({
            method: 'frappe.core.api.file.get_file',
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
                    ${validation_data.headers ? `<p><strong>Found Headers:</strong> ${validation_data.headers.join(', ')}</p>` : ''}
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
        
        // Read CSV file content
        frappe.call({
            method: 'frappe.core.api.file.get_file',
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
                } else {
                    progress_dialog.hide();
                    frappe.msgprint(__('Failed to read CSV file'));
                }
            }
        });
    },
    
    show_progress_dialog: function() {
        const progress_dialog = new frappe.ui.Dialog({
            title: __('Processing CSV Upload'),
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'progress_content',
                    options: `
                        <div class="text-center">
                            <div class="progress mb-3">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 100%"></div>
                            </div>
                            <h6>Processing telemetry data...</h6>
                            <p class="text-muted">Please wait while we update vehicle information from your CSV file.</p>
                            <div class="spinner-border text-primary" role="status">
                                <span class="sr-only">Loading...</span>
                            </div>
                        </div>
                    `
                }
            ]
        });
        
        progress_dialog.show();
        return progress_dialog;
    },
    
    show_results_dialog: function(results) {
        const success_rate = results.total_rows > 0 ? 
            Math.round((results.updated / results.total_rows) * 100) : 0;
        
        let status_color = 'success';
        if (success_rate < 50) status_color = 'danger';
        else if (success_rate < 80) status_color = 'warning';
        
        let content = `
            <div class="csv-upload-results">
                <div class="row mb-3">
                    <div class="col-md-3 text-center">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h4 class="text-primary">${results.total_rows}</h4>
                                <small>Total Rows</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 text-center">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h4 class="text-success">${results.updated}</h4>
                                <small>Updated</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 text-center">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h4 class="text-danger">${results.failed}</h4>
                                <small>Failed</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 text-center">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h4 class="text-warning">${results.skipped}</h4>
                                <small>Skipped</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="progress mb-3">
                    <div class="progress-bar bg-${status_color}" style="width: ${success_rate}%">
                        ${success_rate}% Success Rate
                    </div>
                </div>
        `;
        
        // Show detected format info
        if (results.csv_format) {
            content += `
                <div class="alert alert-info">
                    <strong>Detected Format:</strong> ${results.csv_format.type.replace('_', ' ').toUpperCase()}<br>
                    <strong>Columns Found:</strong> ${results.headers ? results.headers.length : 'Unknown'}
                </div>
            `;
        }
        
        // Show successful updates
        if (results.success_details && results.success_details.length > 0) {
            content += `
                <div class="mt-3">
                    <h6>✅ Successful Updates (Showing first 10):</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Row</th>
                                    <th>TukTuk ID</th>
                                    <th>Device ID</th>
                                    <th>Updates Applied</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            results.success_details.slice(0, 10).forEach(detail => {
                content += `
                    <tr>
                        <td>${detail.row}</td>
                        <td>${detail.tuktuk_id || 'N/A'}</td>
                        <td>${detail.device_id || 'N/A'}</td>
                        <td><small>${detail.updates.join(', ')}</small></td>
                    </tr>
                `;
            });
            
            content += '</tbody></table></div>';
            
            if (results.success_details.length > 10) {
                content += `<small class="text-muted">... and ${results.success_details.length - 10} more</small>`;
            }
            
            content += '</div>';
        }
        
        // Show errors
        if (results.errors && results.errors.length > 0) {
            content += `
                <div class="mt-3">
                    <h6>❌ Errors (Showing first 10):</h6>
                    <div class="alert alert-danger">
                        <ul class="mb-0">
            `;
            
            results.errors.slice(0, 10).forEach(error => {
                content += `<li><small>${error}</small></li>`;
            });
            
            content += '</ul>';
            
            if (results.errors.length > 10) {
                content += `<small>... and ${results.errors.length - 10} more errors</small>`;
            }
            
            content += '</div></div>';
        }
        
        // Show warnings
        if (results.warnings && results.warnings.length > 0) {
            content += `
                <div class="mt-3">
                    <h6>⚠️ Warnings:</h6>
                    <div class="alert alert-warning">
                        <ul class="mb-0">
            `;
            
            results.warnings.forEach(warning => {
                content += `<li><small>${warning}</small></li>`;
            });
            
            content += '</ul></div></div>';
        }
        
        content += '</div>';
        
        const results_dialog = new frappe.ui.Dialog({
            title: __('CSV Upload Results'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'results_content',
                    options: content
                }
            ],
            primary_action: function() {
                results_dialog.hide();
                // Refresh current page if it's a list view
                if (cur_list) {
                    cur_list.refresh();
                }
            },
            primary_action_label: __('Close'),
            secondary_action: function() {
                // Download detailed report
                tuktuk_management.csv_upload.download_detailed_report(results);
            },
            secondary_action_label: __('Download Report')
        });
        
        results_dialog.show();
    },
    
    download_template: function(format_type) {
        frappe.call({
            method: 'tuktuk_management.api.csv_telemetry.get_csv_upload_template',
            args: {
                format_type: format_type
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    const headers = r.message.headers;
                    const csv_content = headers.join(',') + '\n';
                    
                    // Add sample row
                    let sample_row = [];
                    if (format_type === 'telemetry_export') {
                        sample_row = [
                            '860909050379362', '135', 'TUK-001', 'TukTuk', 'KAA123T',
                            'Sunny TukTuk', 'Diani Fleet', 'John Doe', '254712345678', 'Static',
                            'GPS Tracker', '254701234567', '2024-01-01', '2025-01-01', '39.587394',
                            '-4.286028', '0', '45', '10', '12', '25',
                            '2024-12-15 10:30:00', 'OFF', 'ON', 'Valid', '2024-12-15 10:30:00',
                            '0', '79', 'Active'
                        ];
                    } else if (format_type === 'battery_update') {
                        sample_row = ['TUK-001', '75', 'false', '2024-12-15 10:30:00'];
                    } else if (format_type === 'location_update') {
                        sample_row = ['TUK-001', '-4.286028', '39.587394', 'Diani Beach', '2024-12-15 10:30:00'];
                    } else if (format_type === 'vehicle_data') {
                        sample_row = ['TUK-001', '135', '860909050379362', '75', '-4.286028', '39.587394', '0', 'Available'];
                    }
                    
                    const full_content = csv_content + sample_row.join(',');
                    
                    // Create and download file
                    const blob = new Blob([full_content], { type: 'text/csv' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `tuktuk_${format_type}_template.csv`;
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
    },
    
    download_detailed_report: function(results) {
        let report_content = 'CSV Upload Report\n';
        report_content += `Generated: ${frappe.datetime.now_datetime()}\n\n`;
        report_content += `Total Rows: ${results.total_rows}\n`;
        report_content += `Updated: ${results.updated}\n`;
        report_content += `Failed: ${results.failed}\n`;
        report_content += `Skipped: ${results.skipped}\n\n`;
        
        if (results.success_details && results.success_details.length > 0) {
            report_content += 'Successful Updates:\n';
            report_content += 'Row,TukTuk ID,Device ID,Updates\n';
            results.success_details.forEach(detail => {
                report_content += `${detail.row},${detail.tuktuk_id || 'N/A'},${detail.device_id || 'N/A'},"${detail.updates.join('; ')}"\n`;
            });
            report_content += '\n';
        }
        
        if (results.errors && results.errors.length > 0) {
            report_content += 'Errors:\n';
            results.errors.forEach(error => {
                report_content += `"${error}"\n`;
            });
            report_content += '\n';
        }
        
        if (results.warnings && results.warnings.length > 0) {
            report_content += 'Warnings:\n';
            results.warnings.forEach(warning => {
                report_content += `"${warning}"\n`;
            });
        }
        
        // Download report
        const blob = new Blob([report_content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tuktuk_csv_upload_report_${frappe.datetime.get_today()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        frappe.show_alert({
            message: __('Report downloaded successfully'),
            indicator: 'green'
        });
    }
};

// Add CSV upload button to TukTuk Vehicle list
frappe.listview_settings['TukTuk Vehicle'] = frappe.listview_settings['TukTuk Vehicle'] || {};

// Extend the existing onload function
const original_onload = frappe.listview_settings['TukTuk Vehicle'].onload || function() {};

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
frappe.query_reports["Task Analysis"] = {
    "filters": [
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },
        {
            fieldname: "task",
            label: __("Task"),
            fieldtype: "Link",
            options: "Task"
        },
        {
            fieldname: "marked_for_week",
            label: __("Marked for week of"),
            fieldtype: "Date",
            description: "Select first day of week"
        },
        {
            fieldname: "task_owner",
            label: __("Task Owner"),
            fieldtype: "Link",
            options: "User",
            default: frappe.session.user
        },
        {
            fieldname: "show_completed_tasks",
            label: __("Show Completed Tasks"),
            fieldtype: "Check",
        }
    ],

    onload: function(report) {
        // Add refresh button
        report.page.add_inner_button(__('Refresh'), () => {
            report.refresh();
        });

        // Remove existing event handlers before adding new ones
        report.page.wrapper.off('click', '.edit-task-btn');
        report.page.wrapper.off('click', '.copy-task-btn');
        report.page.wrapper.off('click', '.delete-task-btn');

        // Add new event handlers
        report.page.wrapper.on('click', '.edit-task-btn', function() {
            let taskData = JSON.parse(decodeURIComponent($(this).attr('data-task')));
            showEditDialog(taskData, report);
        });

        report.page.wrapper.on('click', '.copy-task-btn', function() {
            let taskData = JSON.parse(decodeURIComponent($(this).attr('data-task')));
            showCopyDialog(taskData, report);
        });

        report.page.wrapper.on('click', '.delete-task-btn', function() {
            let taskData = JSON.parse(decodeURIComponent($(this).attr('data-task')));
            showDeleteDialog(taskData, report);
        });
    },

    "formatter": function(value, row, column, data, default_formatter) {
        if (column.fieldname === "edit_task" && !data.is_project) {
            return `
                <div class="btn-group">
                    <button class="btn btn-xs btn-default edit-task-btn" 
                        data-task='${encodeURIComponent(JSON.stringify(data))}'>
                        <i class="fa fa-pencil"></i>
                    </button>
                    <button class="btn btn-xs btn-info copy-task-btn" 
                        data-task='${encodeURIComponent(JSON.stringify(data))}'>
                        <i class="fa fa-copy"></i>
                    </button>
                    <button class="btn btn-xs btn-danger delete-task-btn" 
                        data-task='${encodeURIComponent(JSON.stringify(data))}'>
                        <i class="fa fa-trash"></i>
                    </button>
                </div>`;
        }
        return default_formatter(value, row, column, data);
    }
};

// Function to show edit dialog
function showEditDialog(taskData, report) {
    let d = new frappe.ui.Dialog({
        title: __('Edit Task'),
        fields: [
            {
                label: __('Task Name'),
                fieldname: 'task',
                fieldtype: 'Data',
                read_only: 1,
                default: taskData.task.trim()
            },
            {
                label: __('Task Owner'),
                fieldname: 'task_owner',
                fieldtype: 'Link',
                options: 'User',
                default: taskData.task_owner
            },
            {
                label: __('Status'),
                fieldname: 'status',
                fieldtype: 'Select',
                options: 'Open\nWorking\nPending Review\nCompleted\nCancelled',
                default: taskData.status
            },
            {
                label: __('Priority'),
                fieldname: 'priority',
                fieldtype: 'Select',
                options: 'Low\nMedium\nHigh',
                default: taskData.priority
            },
            {
                label: __('Expected Start Date'),
                fieldname: 'exp_start_date',
                fieldtype: 'Date',
                default: taskData.exp_start_date
            },
            {
                label: __('Expected End Date'),
                fieldname: 'exp_end_date',
                fieldtype: 'Date',
                default: taskData.exp_end_date
            },
            {
                label: __('Marked For Week'),
                fieldname: 'marked_for_week',
                fieldtype: 'Date',
                default: taskData.marked_for_week
            },
            {
                label: __('Description'),
                fieldname: 'description',
                fieldtype: 'Text Editor',
                default: taskData.description
            }
        ],
        primary_action_label: __('Update Task'),
        secondary_action_label: taskData.is_group ? __('Update All Child Tasks') : null,
        
        primary_action: function() {
            updateTask(d, taskData, report, 'single');
        }
    });

    // Add secondary action for parent tasks
    if (taskData.is_group) {
        d.set_secondary_action(() => {
            updateTask(d, taskData, report, 'all');
        });
    }

    d.show();
}

// Function to show copy dialog
function showCopyDialog(taskData, report) {
    let d = new frappe.ui.Dialog({
        title: __('Copy Task Hierarchy'),
        fields: [
            {
                label: __('Original Task'),
                fieldname: 'task',
                fieldtype: 'Data',
                read_only: 1,
                default: taskData.task.trim()
            },
            {
                label: __('New Project'),
                fieldname: 'new_project',
                fieldtype: 'Link',
                options: 'Project',
                description: __('Leave empty to copy without project assignment')
            },
            {
                label: __('New Task Owner'),
                fieldname: 'new_task_owner',
                fieldtype: 'Link',
                options: 'User',
                description: __('Leave empty to keep original task owners')
            },
            {
                fieldname: 'copy_info',
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info">
                        <p><strong>${__('Note')}:</strong></p>
                        <ul>
                            <li>${__('This will copy the entire task hierarchy including:')}</li>
                            <li>${__('- All child tasks')}</li>
                            <li>${__('- Descriptions')}</li>
                            <li>${__('- Attachments')}</li>
                            ${!taskData.is_project ? 
                                `<li>${__('If no project is selected, the project name will be included in the task subject')}</li>` 
                                : ''}
                        </ul>
                    </div>`
            }
        ],
        primary_action_label: __('Copy'),
        primary_action: function() {
            copyTaskHierarchy(d, taskData, report);
        }
    });

    d.show();
}

// Function to show delete dialog
function showDeleteDialog(taskData, report) {
    let d = new frappe.ui.Dialog({
        title: __('Delete Task'),
        fields: [
            {
                label: __('Task Name'),
                fieldname: 'task',
                fieldtype: 'Data',
                read_only: 1,
                default: taskData.task.trim()
            },
            {
                label: __('Delete Mode'),
                fieldname: 'delete_mode',
                fieldtype: 'Select',
                options: [
                    {label: __('Delete Single Task'), value: 'single'},
                    {label: __('Delete Task with Children'), value: 'all'}
                ],
                default: 'single',
                depends_on: `eval:${taskData.is_group}`,
                mandatory: 1
            },
            {
                fieldname: 'warning',
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-warning">
                        <p><strong>${__('Warning')}:</strong> ${__('This action cannot be undone.')}</p>
                        ${taskData.is_group ? 
                            `<p>${__('This task has child tasks. Selecting "Delete Task with Children" will delete all child tasks as well.')}</p>` 
                            : ''}
                    </div>`
            },
            {
                label: __('Confirmation'),
                fieldname: 'confirmation',
                fieldtype: 'Check',
                label: __('I understand this action cannot be undone'),
                reqd: 1
            }
        ],
        primary_action_label: __('Delete Task'),
        primary_action: function() {
            deleteTask(d, taskData, report);
        }
    });

    d.show();
}

// Function to handle task update
function updateTask(dialog, taskData, report, update_mode) {
    let values = dialog.get_values();
    
    if (!values) return;

    // Validate dates
    if (values.exp_start_date && values.exp_end_date && 
        frappe.datetime.str_to_obj(values.exp_start_date) > frappe.datetime.str_to_obj(values.exp_end_date)) {
        frappe.throw(__("Expected End Date cannot be before Expected Start Date"));
        return;
    }

    frappe.call({
        method: 'task_management.task_management.report.task_analysis.task_analysis.update_task',
        args: {
            task_data: values,
            update_mode: update_mode
        },
        freeze: true,
        freeze_message: update_mode === 'single' ? 
            __('Updating Task...') : 
            __('Updating Task and Child Tasks...'),
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: update_mode === 'single' ? 
                        __('Task updated successfully') : 
                        __('Task and child tasks updated successfully'),
                    indicator: 'green'
                });
                dialog.hide();
                report.refresh();
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: r.exc
                });
            }
        }
    });
}

// Function to handle task deletion
function deleteTask(dialog, taskData, report) {
    let values = dialog.get_values();
    
    if (!values.confirmation) {
        frappe.throw(__('Please confirm deletion'));
        return;
    }

    frappe.call({
        method: 'task_management.task_management.report.task_analysis.task_analysis.delete_task',
        args: {
            task_data: values,
            delete_mode: values.delete_mode || 'single'
        },
        freeze: true,
        freeze_message: values.delete_mode === 'single' ? 
            __('Deleting Task...') : 
            __('Deleting Task and Child Tasks...'),
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: values.delete_mode === 'single' ? 
                        __('Task deleted successfully') : 
                        __('Task and child tasks deleted successfully'),
                    indicator: 'green'
                });
                dialog.hide();
                report.refresh();
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: r.exc
                });
            }
        }
    });
}

// Function to handle task hierarchy copying
function copyTaskHierarchy(dialog, taskData, report) {
    let values = dialog.get_values();
    
    frappe.call({
        method: 'task_management.task_management.report.task_analysis.task_analysis.copy_task_hierarchy',
        args: {
            task_data: taskData,
            new_project: values.new_project,
            new_task_owner: values.new_task_owner
        },
        freeze: true,
        freeze_message: __('Copying Task Hierarchy...'),
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: __('Task hierarchy copied successfully'),
                    indicator: 'green'
                });
                dialog.hide();
                report.refresh();
                
                // Open the new task in a new tab
                if (r.message && r.message.new_task_id) {
                    frappe.set_route('Form', 'Task', r.message.new_task_id);
                }
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: r.exc
                });
            }
        }
    });
}
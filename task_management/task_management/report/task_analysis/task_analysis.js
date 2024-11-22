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
        report.page.add_inner_button(__('Refresh'), () => {
            report.refresh();
        });
    },

   "formatter": function(value, row, column, data, default_formatter) {
    console.log("Formatting column:", column.fieldname);
    console.log("Is Project:", data.is_project);
    
    if (column.fieldname === "edit_task" && !data.is_project) {
        console.log("Generating Edit Task Button");
        return `<button class="btn btn-xs btn-default edit-task-btn" 
                    data-task='${encodeURIComponent(JSON.stringify(data))}'>
                    Edit Task
                </button>`;
    }
    return default_formatter(value, row, column, data);
},
    onload: function(report) {
		console.log("hooo")
        // Handle edit button click
        report.page.wrapper.on('click', '.edit-task-btn', function() {
            // Parse the task data from the button's data attribute
            let taskData = JSON.parse(decodeURIComponent($(this).attr('data-task')));
            
            // Create the edit dialog
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
                
                // Primary action - update single task
                primary_action: function() {
                    let values = d.get_values();
                    
                    // Validate input
                    if (!values) return;

                    frappe.call({
                        method: 'task_management.task_management.report.task_analysis.task_analysis.update_task',
                        args: {
                            task_data: values,
                            update_mode: 'single'
                        },
                        freeze: true,
                        freeze_message: __('Updating Task...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Task updated successfully'),
                                    indicator: 'green'
                                });
                                d.hide();
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
            });

            // Add secondary action for parent tasks to update all child tasks
            if (taskData.is_group) {
                d.set_secondary_action(function() {
                    let values = d.get_values();
                    
                    // Validate input
                    if (!values) return;

                    frappe.call({
                        method: 'task_management.task_management.report.task_analysis.task_analysis.update_task',
                        args: {
                            task_data: values,
                            update_mode: 'all'
                        },
                        freeze: true,
                        freeze_message: __('Updating Task and Child Tasks...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Task and child tasks updated successfully'),
                                    indicator: 'green'
                                });
                                d.hide();
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
                });
            }

            // Show the dialog
            d.show();
        });
    }
};
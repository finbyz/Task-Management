import frappe
from frappe import _
from frappe.utils import getdate, cstr, today

def validate(doc, method):
    """
    Validate and update task group fields when a task is saved
    
    Args:
        doc (Document): Task document being saved
        method (str): Trigger method (before_save, validate, etc.)
    """
    # Skip if this is not a task or if no parent task exists
    if doc.doctype != 'Task' or not doc.parent_task:
        return
    
    try:
        update_parent_task_group_fields(doc.parent_task)
    except Exception as e:
        # Log detailed error for tracking
        frappe.log_error(
            title="Task Group Field Update Error", 
            message=f"Error updating parent task group {doc.parent_task}: {str(e)}"
        )
        # Throw a user-friendly error
        frappe.throw(_(f"Could not update parent task group: {str(e)}"))

def update_parent_task_group_fields(parent_task_name):
    """
    Recursively update parent task group fields in specific order:
    1. Expected Start Date (earliest)
    2. Expected End Date (latest)
    3. Marked for Week (earliest)
    4. Status (most critical)
    
    Args:
        parent_task_name (str): Name of the parent task to update
    """
    # Comprehensive status priority mapping
    status_priority = {
        'Unplanned': 1,
        'Planned': 2,
        'Scheduled': 3,
        'In Progress': 4,
        'Completed': 5,
        'Cancelled': 6,
        # Fallback for unexpected statuses
        '': 5
    }
    
    # Get the parent task document
    try:
        parent_task = frappe.get_doc('Task', parent_task_name)
    except frappe.DoesNotExistError:
        frappe.log_error(f"Parent task {parent_task_name} does not exist")
        return
    
    # Get all direct child tasks of this task (non-group tasks only)
    child_tasks = frappe.get_all('Task', 
        filters={
            'parent_task': parent_task_name,
        },
        fields=[
            'name', 
            'status', 
            'workflow_state',
            'custom_marked_for_week_of_select_1st_day_of_the_week', 
            'exp_start_date',
            'exp_end_date'
        ]
    )
    
    # If no child tasks, we can't update
    if not child_tasks:
        return
    
    # 1. Find Earliest Start Date
    start_dates = [
        getdate(task.exp_start_date) 
        for task in child_tasks 
        if task.exp_start_date
    ]
    if start_dates:
        parent_task.exp_start_date = min(start_dates)
    
    # 2. Find Latest End Date
    end_dates = [
        getdate(task.exp_end_date) 
        for task in child_tasks 
        if task.exp_end_date
    ]
    if end_dates:
        parent_task.exp_end_date = max(end_dates)
    
    # 3. Find Earliest Marked for Week Date
    marked_for_week_dates = [
        getdate(task.custom_marked_for_week_of_select_1st_day_of_the_week) 
        for task in child_tasks 
        if task.custom_marked_for_week_of_select_1st_day_of_the_week
    ]
    if marked_for_week_dates:
        parent_task.custom_marked_for_week_of_select_1st_day_of_the_week = min(marked_for_week_dates)
    
    # 4. Determine Lowest Status (most critical)
    try:
        lowest_status = min(
            (task.status for task in child_tasks if task.status), 
            key=lambda x: status_priority.get(x, 5)
        )
        parent_task.status = lowest_status
        
        # Update the workflow state
        if lowest_status == 'Cancelled':
            parent_task.workflow_state = 'Cancelled'
        elif lowest_status == 'Completed':
            parent_task.workflow_state = 'Completed'
        elif lowest_status == 'In-Progress':
            parent_task.workflow_state = "In Progress"
        else:
            parent_task.workflow_state = lowest_status
    except ValueError:
        # No valid status found
        frappe.log_error(f"No valid status found for task group {parent_task_name}")
    
    # Save the parent task with minimal checks
    try:
        parent_task.flags.ignore_version = True
        parent_task.flags.ignore_validate = True
        parent_task.save(ignore_permissions=True)
    except Exception as save_error:
        frappe.log_error(
            title="Task Group Save Error", 
            message=f"Could not save task group {parent_task_name}: {str(save_error)}"
        )
    
    # Recursively update grandparent if exists
    grandparent = frappe.get_value('Task', parent_task_name, 'parent_task')
    if grandparent:
        update_parent_task_group_fields(grandparent)
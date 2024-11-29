import frappe
from frappe import _
from frappe.utils import getdate, cstr

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
        # Update parent task group fields
        update_parent_task_group_fields(doc.parent_task)
    except Exception as e:
        frappe.log_error(f"Error updating parent task group fields: {str(e)}")
        frappe.throw(_("Error updating parent task group: {0}").format(str(e)))

def update_parent_task_group_fields(parent_task_name):
    """
    Recursively update parent task group fields
    
    Args:
        parent_task_name (str): Name of the parent task to update
    """
    # Get the parent task document
    parent_task = frappe.get_doc('Task', parent_task_name)
    
    # Get all direct child tasks of this task
    child_tasks = frappe.get_all('Task', 
        filters={'parent_task': parent_task_name},
        fields=[
            'name', 
            'status', 
            'custom_marked_for_week_of_select_1st_day_of_the_week', 
            'exp_end_date'
        ]
    )
    
    if not child_tasks:
        return
    
    # Status Priority Mapping
    status_priority = {
        'Cancelled': 0,
        'Open': 1,
        'Working': 2,
        'Pending Review': 3,
        'Completed': 4
    }
    
    # 1. Determine Lowest Status
    status_list = [task.status for task in child_tasks if task.status]
    if status_list:
        parent_task.status = min(status_list, key=lambda x: status_priority.get(x, 1))
    
    # 2. Find Earliest Marked for Week Date
    marked_for_week_dates = [
        getdate(task.custom_marked_for_week_of_select_1st_day_of_the_week) 
        for task in child_tasks 
        if task.custom_marked_for_week_of_select_1st_day_of_the_week
    ]
    if marked_for_week_dates:
        parent_task.custom_marked_for_week_of_select_1st_day_of_the_week = min(marked_for_week_dates)
    
    # 3. Find Latest End Date
    end_dates = [
        getdate(task.exp_end_date) 
        for task in child_tasks 
        if task.exp_end_date
    ]
    if end_dates:
        parent_task.exp_end_date = max(end_dates)
    
    # Save the parent task with minimal checks
    parent_task.flags.ignore_version = True
    parent_task.flags.ignore_validate = True
    parent_task.save(ignore_permissions=True)
    
    # Recursively update grandparent if exists
    grandparent = frappe.get_value('Task', parent_task_name, 'parent_task')
    if grandparent:
        update_parent_task_group_fields(grandparent)
import frappe
from frappe import _
from frappe.utils import getdate, add_to_date

def run_task_group_update():
    """
    Scheduled method to update all task group fields
    """
    try:
        update_task_group_fields()
        return "Task group fields updated successfully"
    except Exception as e:
        frappe.log_error(f"Error in task group update: {str(e)}")
        return f"Error: {str(e)}"
    
def update_task_group_fields():
    """
    Main function to update task group fields recursively
    Updates for all task groups in the system
    """
    # Get all task groups (tasks with child tasks)
    task_groups = frappe.get_all('Task', 
        filters={'is_group': 1},
        fields=['name']
    )
    
    for task_group in task_groups:
        update_task_group_recursive(task_group.name)

def update_task_group_recursive(task_group_name):
    """
    Recursively update task group fields
    
    Args:
        task_group_name (str): Name of the task group to update
    """
    # First, update child tasks to ensure bottom-up update
    child_tasks = frappe.get_all('Task', 
        filters={'parent_task': task_group_name},
        fields=['name']
    )
    
    for child_task in child_tasks:
        # Recursively update child tasks first (if they are groups)
        if frappe.get_value('Task', child_task.name, 'is_group'):
            update_task_group_recursive(child_task.name)
    
    # Get all direct child tasks of this group
    child_tasks = frappe.get_all('Task', 
        filters={'parent_task': task_group_name},
        fields=[
            'name', 
            'status', 
            'custom_marked_for_week_of_select_1st_day_of_the_week', 
            'exp_end_date'
        ]
    )
    
    if not child_tasks:
        return
    
    # 1. Update Status (lowest status)
    status_priority = {
        'Cancelled': 0,
        'Open': 1,
        'Working': 2,
        'Pending Review': 3,
        'Completed': 4
    }
    
    lowest_status = min(child_tasks, key=lambda x: status_priority.get(x.status, 1))
    
    # 2. Update Marked for Week (earliest date)
    marked_for_week_dates = [
        getdate(task.custom_marked_for_week_of_select_1st_day_of_the_week) 
        for task in child_tasks 
        if task.custom_marked_for_week_of_select_1st_day_of_the_week
    ]
    
    # 3. Update End Date (latest end date of children)
    end_dates = [
        getdate(task.exp_end_date) 
        for task in child_tasks 
        if task.exp_end_date
    ]
    
    try:
        # Update the task group
        task_group = frappe.get_doc('Task', task_group_name)
        
        # Update status
        if lowest_status:
            task_group.status = lowest_status.status
        
        # Update marked for week (earliest)
        if marked_for_week_dates:
            task_group.custom_marked_for_week_of_select_1st_day_of_the_week = min(marked_for_week_dates)
        
        # Update end date (latest)
        if end_dates:
            task_group.exp_end_date = max(end_dates)
        
        # Save with minimal checks
        task_group.flags.ignore_version = True
        task_group.save(ignore_permissions=True)
    
    except Exception as e:
        frappe.log_error(f"Error updating task group {task_group_name}: {str(e)}")
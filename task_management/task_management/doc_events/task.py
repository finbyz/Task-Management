import frappe
from frappe import _
from frappe.utils import getdate, add_to_date

def before_validate(self,method):
    if self.status == "Planned" and (self.custom_marked_for_week_of_select_1st_day_of_the_week == None or self.custom_marked_for_week_of_select_1st_day_of_the_week == ""):
        frappe.throw("Please specify 'Mark for Week Of' to set this task's status to Planned.")
        
    if self.status == "Scheduled" and ((self.exp_start_date == None or self.exp_start_date == "") or (self.exp_end_date == None or self.exp_end_date == "")):
        frappe.throw("Expected Start Date and Expected End Date are required to set this task's status to Scheduled.")
    
    if self.custom_marked_for_week_of_select_1st_day_of_the_week:
        self.custom_allow_changing_mark_of_week = 0
    
    if self.exp_start_date:
        self.custom_allow_changing_expected_start = 0
    
    if self.exp_end_date:
        self.custom_allow_changing_expected_end = 0

def run_task_group_update(self,method):
    """
    Scheduled method to update all task group fields
    """
    try:
        # Log start of update process
        frappe.log("Starting task group update process")
        
        # Get all task groups (tasks with child tasks)
        task_groups = frappe.get_all('Task', 
            filters={'is_group': 1},
            fields=['name']
        )
        
        # Track update statistics
        total_groups_updated = 0
        
        # Process each task group from bottom to top
        for task_group in task_groups:
            try:
                update_task_group_recursive(task_group.name)
                total_groups_updated += 1
            except Exception as group_update_error:
                frappe.log_error(f"Error updating task group {task_group.name}: {str(group_update_error)}")
        
        # Log completion
        frappe.log(f"Task group update completed. Total groups updated: {total_groups_updated}")
        return f"Task group fields updated successfully. {total_groups_updated} groups processed."
    
    except Exception as e:
        frappe.log_error(f"Critical error in task group update: {str(e)}")
        return f"Error: {str(e)}"

def update_task_group_recursive(task_group_name):
    """
    Recursively update task group fields
    
    Args:
        task_group_name (str): Name of the task group to update
    """
    # Retrieve all child tasks, including nested groups
    all_child_tasks = frappe.get_all('Task', 
        filters={'parent_task': task_group_name},
        fields=[
            'name', 
            'is_group',
            'status', 
            'custom_marked_for_week_of_select_1st_day_of_the_week', 
            'exp_end_date'
        ]
    )
    
    # First, recursively update any child task groups
    for child_task in all_child_tasks:
        if child_task.is_group:
            update_task_group_recursive(child_task.name)
    
    # Filter out only non-group child tasks for aggregation
    direct_child_tasks = [
        task for task in all_child_tasks 
        if not task.is_group
    ]
    
    # If no direct child tasks, exit
    if not direct_child_tasks:
        return
    
    # Status priority mapping
    status_priority = {
        'Cancelled': 0,
        'Open': 1,
        'Working': 2,
        'Pending Review': 3,
        'Completed': 4
    }
    
    try:
        # 1. Determine lowest status (most critical)
        lowest_status = min(
            (task.status for task in direct_child_tasks), 
            key=lambda x: status_priority.get(x, 999)
        )
        
        # 2. Find earliest 'marked for week' date
        marked_for_week_dates = [
            getdate(task.custom_marked_for_week_of_select_1st_day_of_the_week) 
            for task in direct_child_tasks 
            if task.custom_marked_for_week_of_select_1st_day_of_the_week
        ]
        
        # 3. Find latest end date
        end_dates = [
            getdate(task.exp_end_date) 
            for task in direct_child_tasks 
            if task.exp_end_date
        ]
        
        # Update the task group document
        task_group = frappe.get_doc('Task', task_group_name)
        
        # Update fields
        task_group.status = lowest_status
        
        if marked_for_week_dates:
            task_group.custom_marked_for_week_of_select_1st_day_of_the_week = min(marked_for_week_dates)
        
        if end_dates:
            task_group.exp_end_date = max(end_dates)
        
        # Save with minimal checks
        task_group.flags.ignore_version = True
        task_group.save(ignore_permissions=True)
    
    except Exception as e:
        frappe.log_error(f"Error processing task group {task_group_name}: {str(e)}")
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "task",
            "label": _("Task"),
            "fieldtype": "Data",
            "width": 300
        },
        {
            "fieldname": "task_owner",
            "label": _("Task Owner"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "marked_for_week",
            "label": _("Marked For Week Of"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "exp_start_date",
            "label": _("Expected Start Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "exp_end_date",
            "label": _("Expected End Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Select",
            "options": "Open\nWorking\nPending Review\nCompleted\nCancelled",
            "width": 120
        },
        {
            "fieldname": "priority",
            "label": _("Priority"),
            "fieldtype": "Select",
            "options": "Low\nMedium\nHigh",
            "width": 100
        },
        {
            "fieldname": "description",
            "label": _("Description"),
            "fieldtype": "Text Editor",
            "width": 300
        },
        {
            "fieldname": "edit_task",
            "label": _("Edit Task"),
            "fieldtype": "Button",
            "width": 100
        }
    ]

def get_data(filters):
    tasks = get_tasks(filters)
    projects = get_projects(filters)
    
    if not tasks and not projects:
        return []
    
    return prepare_data(filters, projects, tasks)

def get_projects(filters):
    conditions = ""
    if filters.get('project'):
        conditions += f" WHERE name = '{filters.get('project')}'"
    
    return frappe.db.sql("""
        SELECT 
            name,
            project_name as subject,
            status,
            priority,
            expected_start_date,
            expected_end_date,
            2 as is_group,  /* 2 for project to differentiate from tasks */
            1 as is_project
        FROM
            `tabProject`
        {conditions}
        ORDER BY name
    """.format(conditions=conditions), as_dict=True)

def get_tasks(filters):
    conditions = []
    task_condition = ""
    
    if filters.get('project'):
        conditions.append(f"project = '{filters.get('project')}'")
    
    if filters.get('task'):
        task_project = frappe.db.get_value('Task', filters.get('task'), 'project')
        if task_project:
            conditions.append(f"project = '{task_project}'")
            task_condition = f"""
                (
                    name = '{filters.get('task')}' OR 
                    parent_task = '{filters.get('task')}' OR 
                    name IN (
                        SELECT name FROM `tabTask` 
                        WHERE parent_task IN (
                            SELECT name FROM `tabTask` 
                            WHERE parent_task = '{filters.get('task')}'
                        )
                    )
                )
            """
    
    if filters.get('marked_for_week'):
        conditions.append(
            f"custom_marked_for_week_of_select_1st_day_of_the_week = '{filters.get('marked_for_week')}'"
        )
    
    if not filters.get('show_completed_tasks'):
        conditions.append("status != 'Completed'")
    
    if filters.get("task_owner"):
        conditions.append(f"custom_task_owner = '{filters.get('task_owner')}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    if task_condition:
        where_clause += f" AND {task_condition}"
    
    return frappe.db.sql(f"""
        SELECT 
            name,
            subject,
            IFNULL(parent_task, '') as parent_task,
            project,
            status,
            custom_task_owner as task_owner,
            priority,
            description,
            exp_start_date,
            exp_end_date,
            CASE WHEN EXISTS (
                SELECT 1 FROM `tabTask` t2 
                WHERE t2.parent_task = `tabTask`.name
            ) THEN 1 ELSE 0 END as is_group,
            custom_marked_for_week_of_select_1st_day_of_the_week as marked_for_week,
            CASE 
                WHEN parent_task IS NULL THEN 'grandparent'
                ELSE 'child'
            END as task_type,
            0 as is_project
        FROM
            `tabTask`
        WHERE 
            {where_clause}
        ORDER BY project, parent_task, name
    """, as_dict=True)

def prepare_data(filters, projects, tasks):
    data = []
    project_task_map = {}
    parent_children_map = {}
    
    for task in tasks:
        parent_children_map.setdefault(task.parent_task or task.project, []).append(task)
        project_task_map.setdefault(task.project, []).append(task)
    
    for project in projects:
        project_tasks = project_task_map.get(project.name, [])
        
        if project_tasks:
            data.append(frappe._dict({
                "task": cstr(project.subject),
                "status": project.status,
                "priority": project.priority,
                "description": "",
                "marked_for_week": None,
                "task_owner": "",
                "indent": 0,
                "exp_start_date": project.expected_start_date,
                "exp_end_date": project.expected_end_date,
                "is_group": project.is_group,
                "is_project": project.is_project
            }))
            
            grandparent_tasks = [t for t in project_tasks if t.task_type == 'grandparent']
            other_tasks = [t for t in project_tasks if t.task_type != 'grandparent']
            
            for gp_task in grandparent_tasks:
                add_task_to_data(data, gp_task, parent_children_map, 1)
            
            if not grandparent_tasks:
                other_tasks.sort(key=lambda x: (x.parent_task or '', x.name))
                
                for task in other_tasks:
                    level = 0
                    current_parent = task.parent_task
                    while current_parent:
                        level += 1
                        parent_info = frappe.db.get_value('Task', current_parent, 
                            ['parent_task'], as_dict=True)
                        current_parent = parent_info.get('parent_task') if parent_info else None
                    
                    task_name = '  ' * level + cstr(task.subject)
                    data.append(frappe._dict({
                        "task": task_name,
                        "task_owner": task.task_owner,
                        "exp_start_date": task.exp_start_date,
                        "exp_end_date": task.exp_end_date,
                        "status": task.status,
                        "priority": task.priority,
                        "description": task.description,
                        "marked_for_week": task.marked_for_week,
                        "indent": level,
                        "is_group": task.is_group,
                        "is_project": task.is_project
                    }))
    
    return data

def add_task_to_data(data, task, parent_children_map, level):
    task_name = '  ' * level + cstr(task.subject)
    data.append(frappe._dict({
        "task": task_name,
        "task_owner": task.task_owner,
        "exp_start_date": task.exp_start_date,
        "exp_end_date": task.exp_end_date,
        "status": task.status,
        "priority": task.priority,
        "description": task.description,
        "marked_for_week": task.marked_for_week,
        "indent": level,
        "is_group": task.is_group,
        "is_project": task.is_project
    }))
    
    if task.name in parent_children_map:
        children = parent_children_map[task.name]
        children.sort(key=lambda x: x.name)
        for child in children:
            add_task_to_data(data, child, parent_children_map, level + 1)

import frappe
from frappe import _
from frappe.utils import getdate

@frappe.whitelist()
def update_task(task_data, update_mode='single'):
    """
    Update task and optionally its child tasks
    
    Args:
        task_data (dict): Task data to update
        update_mode (str): 'single' for current task only, 'all' for task and all children
    """
    if not isinstance(task_data, dict):
        task_data = frappe.parse_json(task_data)
        
    if not task_data:
        frappe.throw(_("No task data provided"))
    
    try:
        # Get the task name (remove any indentation spaces)
        task_name = task_data.get('task', '').strip()
        if not task_name:
            frappe.throw(_("Task name is required"))
            
        # Get the actual task name from the display name (removes indentation)
        actual_task_name = get_actual_task_name(task_name)
        if not actual_task_name:
            frappe.throw(_("Task not found"))
        
        # Update the current task
        update_single_task(actual_task_name, task_data)
        
        # If update_mode is 'all', update all child tasks
        if update_mode == 'all':
            child_tasks = get_all_child_tasks(actual_task_name)
            for child_task in child_tasks:
                update_single_task(child_task.name, task_data)
        
        frappe.db.commit()
        
        return {
            "message": _("Task updated successfully") if update_mode == 'single' 
                      else _("Task and all child tasks updated successfully")
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), _("Task Update Error"))
        frappe.throw(_("Error updating task: {0}").format(str(e)))

def update_single_task(task_name, task_data):
    """
    Update a single task with the provided data
    
    Args:
        task_name (str): Name of the task to update
        task_data (dict): New data for the task
    """
    task = frappe.get_doc('Task', task_name)
    
    # Map of frontend field names to database field names
    field_mapping = {
        'task_owner': 'custom_task_owner',
        'status': 'status',
        'priority': 'priority',
        'exp_start_date': 'exp_start_date',
        'exp_end_date': 'exp_end_date',
        'marked_for_week': 'custom_marked_for_week_of_select_1st_day_of_the_week',
        'description': 'description'
    }
    
    # Update each field if provided in task_data
    for frontend_field, db_field in field_mapping.items():
        if task_data.get(frontend_field):
            # Handle date fields
            if frontend_field in ['exp_start_date', 'exp_end_date', 'marked_for_week']:
                task.set(db_field, getdate(task_data.get(frontend_field)))
            else:
                task.set(db_field, task_data.get(frontend_field))
    
    # Validate task dates
    if task.exp_start_date and task.exp_end_date and task.exp_start_date > task.exp_end_date:
        frappe.throw(_("Expected End Date cannot be before Expected Start Date"))
    
    # Save the task with validate and notify flags
    task.flags.ignore_version = True  # Skip version creation
    task.save(ignore_permissions=True)
    
    # Add a comment to the task
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Task",
        "reference_name": task_name,
        "content": _("Task updated via Task Analysis Report by {0}").format(frappe.session.user)
    }).insert(ignore_permissions=True)

def get_actual_task_name(display_name):
    """
    Get the actual task name from the display name by removing indentation
    
    Args:
        display_name (str): Task name as displayed in the report (may include indentation)
    
    Returns:
        str: Actual task name from the database
    """
    # Remove any leading/trailing spaces and indentation
    clean_name = display_name.strip()
    
    # Try to find the task by subject
    task_name = frappe.db.get_value('Task', 
        {'subject': clean_name}, 
        'name'
    )
    
    if not task_name:
        # If not found, try to find by name directly
        task_name = frappe.db.get_value('Task', 
            {'name': clean_name}, 
            'name'
        )
    
    return task_name

def get_all_child_tasks(parent_task):
    """
    Get all child tasks recursively using a CTE (Common Table Expression)
    
    Args:
        parent_task (str): Parent task name
    
    Returns:
        list: List of child task documents
    """
    # First try using CTE if supported by the database
    try:
        return frappe.db.sql("""
            WITH RECURSIVE task_tree AS (
                -- Base case: direct children
                SELECT name, parent_task, 1 as level
                FROM `tabTask`
                WHERE parent_task = %(parent)s
                
                UNION ALL
                
                -- Recursive case: children of children
                SELECT t.name, t.parent_task, tt.level + 1
                FROM `tabTask` t
                INNER JOIN task_tree tt ON t.parent_task = tt.name
            )
            SELECT name 
            FROM task_tree
            ORDER BY level, name
        """, {'parent': parent_task}, as_dict=1)
    
    except Exception:
        # Fallback to non-recursive approach if CTE is not supported
        child_tasks = []
        tasks_to_process = [parent_task]
        processed_tasks = set()
        
        while tasks_to_process:
            current_task = tasks_to_process.pop(0)
            if current_task in processed_tasks:
                continue
                
            processed_tasks.add(current_task)
            
            children = frappe.get_all('Task',
                filters={'parent_task': current_task},
                fields=['name']
            )
            
            child_tasks.extend(children)
            tasks_to_process.extend([child.name for child in children])
        
        return child_tasks

def validate_task_permissions(task_name):
    """
    Validate if the current user has permission to edit the task
    
    Args:
        task_name (str): Name of the task to check
    """
    if not frappe.has_permission('Task', 'write', task_name):
        frappe.throw(_("No permission to edit task: {0}").format(task_name))
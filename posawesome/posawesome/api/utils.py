from __future__ import annotations
import frappe

@frappe.whitelist()
def get_active_pos_profile(user=None):
    """Return the active POS profile for the given user."""
    user = user or frappe.session.user
    profile = frappe.db.get_value("POS Profile User", {"user": user}, "parent")
    if not profile:
        profile = frappe.db.get_single_value("POS Settings", "pos_profile")
    if not profile:
        return None
    return frappe.get_doc("POS Profile", profile).as_dict()

@frappe.whitelist()
def get_default_warehouse(company=None):
    """Return the default warehouse for the given company."""
    company = company or frappe.defaults.get_default("company")
    if not company:
        return None
    warehouse = frappe.db.get_value("Company", company, "default_warehouse")
    if not warehouse:
        warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    return warehouse

@frappe.whitelist()
def debug_pos_profile():
    """Debug function to check POS Profile data."""
    current_user = frappe.session.user
    
    # Check POS Profiles
    pos_profiles = frappe.get_all('POS Profile', fields=['name', 'user', 'company', 'disabled'])
    
    # Check user-specific profiles  
    user_profiles = frappe.get_all('POS Profile', filters={'user': current_user, 'disabled': 0}, fields=['name', 'company'])
    
    # Try to get active profile
    try:
        active_profile = get_active_pos_profile()
        profile_result = active_profile.get('name') if active_profile else None
    except Exception as e:
        profile_result = f"Error: {str(e)}"
    
    return {
        "current_user": current_user,
        "all_profiles": pos_profiles,
        "user_profiles": user_profiles,
        "active_profile": profile_result
    }

#!/usr/bin/env python3
"""
Debug script for POS Profile and Opening Shift issues
Run this to check if the backend data is properly configured
"""

import frappe
from posawesome.posawesome.api.shifts import check_opening_shift

def debug_pos_setup():
    """Debug POS Profile and Opening Shift setup"""
    print("=== POS Profile Debug Information ===")
    
    # Check current user
    user = frappe.session.user
    print(f"Current User: {user}")
    
    # Check if user has any POS Profiles
    pos_profiles = frappe.db.get_all(
        "POS Profile",
        filters={"disabled": 0},
        fields=["name", "company", "warehouse", "disabled"]
    )
    print(f"\nAvailable POS Profiles: {len(pos_profiles)}")
    for profile in pos_profiles:
        print(f"  - {profile.name} (Company: {profile.company}, Warehouse: {profile.warehouse})")
    
    # Check POS Profile User permissions
    user_profiles = frappe.db.get_all(
        "POS Profile User",
        filters={"user": user},
        fields=["parent", "user"]
    )
    print(f"\nPOS Profiles assigned to {user}: {len(user_profiles)}")
    for up in user_profiles:
        print(f"  - {up.parent}")
    
    # Check Opening Shifts
    opening_shifts = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
        },
        fields=["name", "pos_profile", "period_start_date", "status"],
        order_by="period_start_date desc",
    )
    print(f"\nOpen POS Opening Shifts for {user}: {len(opening_shifts)}")
    for shift in opening_shifts:
        print(f"  - {shift.name} (Profile: {shift.pos_profile}, Start: {shift.period_start_date})")
    
    # Test the check_opening_shift function
    print(f"\n=== Testing check_opening_shift function ===")
    try:
        result = check_opening_shift(user)
        if result:
            print(f"SUCCESS: Opening shift found")
            print(f"  - Opening Shift: {result['pos_opening_shift'].name}")
            print(f"  - POS Profile: {result['pos_profile'].name}")
            print(f"  - Company: {result['company'].name}")
        else:
            print("INFO: No opening shift found - this will trigger the opening dialog")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pos_setup()

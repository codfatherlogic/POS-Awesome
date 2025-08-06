#!/usr/bin/env python3

import frappe

def debug_pos_profile():
    # Initialize site
    frappe.init('pos')
    frappe.connect()
    
    print("=" * 50)
    print("POS PROFILE DEBUG SCRIPT")
    print("=" * 50)
    
    # Check current user
    current_user = frappe.session.user
    print(f"Current user: {current_user}")
    
    # Check all POS Profiles
    pos_profiles = frappe.get_all('POS Profile', 
                                  fields=['name', 'user', 'company', 'disabled', 'warehouse'],
                                  order_by='creation desc')
    print(f"\nAll POS Profiles ({len(pos_profiles)}):")
    for profile in pos_profiles:
        print(f"  - {profile.name}: user={profile.user}, company={profile.company}, disabled={profile.disabled}")
    
    # Check user-specific profiles
    user_profiles = frappe.get_all('POS Profile', 
                                  filters={'user': current_user, 'disabled': 0},
                                  fields=['name', 'company', 'warehouse'])
    print(f"\nUser-specific profiles for {current_user} ({len(user_profiles)}):")
    for profile in user_profiles:
        print(f"  - {profile.name}: company={profile.company}, warehouse={profile.warehouse}")
    
    # Test get_active_pos_profile function
    try:
        from posawesome.posawesome.api.utils import get_active_pos_profile
        active_profile = get_active_pos_profile()
        print(f"\nActive POS Profile from utils: {active_profile}")
    except Exception as e:
        print(f"\nError getting active profile: {e}")
    
    # Check if there's a default company profile
    try:
        company_profiles = frappe.get_all('POS Profile', 
                                         filters={'disabled': 0},
                                         fields=['name', 'company', 'user'],
                                         limit=1)
        print(f"\nAny enabled POS Profile: {company_profiles}")
    except Exception as e:
        print(f"\nError getting company profiles: {e}")
    
    print("=" * 50)

if __name__ == "__main__":
    debug_pos_profile()

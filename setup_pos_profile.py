import os
import sys
import frappe

# Change to the correct directory
os.chdir('/Users/sammishthundiyil/frappe-bench-ai')

# Initialize Frappe
frappe.init(site='pos')
frappe.connect()

try:
    # Check if any companies exist
    companies = frappe.get_all('Company', limit=1)
    if not companies:
        print("❌ No companies found. Please create a company first.")
        frappe.destroy()
        exit(1)
    
    company = companies[0].name
    print(f"📊 Using company: {company}")
    
    # Get or create required master data
    warehouses = frappe.get_all('Warehouse', {'company': company}, limit=1)
    warehouse = warehouses[0].name if warehouses else None
    
    territories = frappe.get_all('Territory', limit=1)
    territory = territories[0].name if territories else 'All Territories'
    
    price_lists = frappe.get_all('Price List', {'selling': 1}, limit=1)
    selling_price_list = price_lists[0].name if price_lists else 'Standard Selling'
    
    cost_centers = frappe.get_all('Cost Center', {'company': company}, limit=1)
    cost_center = cost_centers[0].name if cost_centers else None
    
    # Create POS Profile
    pos_profile_name = 'Main POS Profile'
    
    # Check if it already exists
    if frappe.db.exists('POS Profile', pos_profile_name):
        print(f"📋 POS Profile '{pos_profile_name}' already exists, updating...")
        pos_profile = frappe.get_doc('POS Profile', pos_profile_name)
        pos_profile.posa_show_oem_part_number_in_list = 1
        pos_profile.disabled = 0
        
        # Ensure current user is in the applicable users
        user_exists = False
        for row in pos_profile.applicable_for_users:
            if row.user == frappe.session.user:
                user_exists = True
                break
        
        if not user_exists:
            pos_profile.append('applicable_for_users', {
                'user': frappe.session.user
            })
        
        pos_profile.save()
        print(f"✅ Updated POS Profile: {pos_profile.name}")
    else:
        print(f"🆕 Creating new POS Profile: {pos_profile_name}")
        pos_profile = frappe.get_doc({
            'doctype': 'POS Profile',
            'naming_series': 'POS-PROFILE-.#####',
            'company': company,
            'currency': frappe.get_cached_value('Company', company, 'default_currency') or 'USD',
            'warehouse': warehouse,
            'territory': territory,
            'selling_price_list': selling_price_list,
            'cost_center': cost_center,
            'disabled': 0,
            'posa_show_oem_part_number_in_list': 1,  # Enable OEM part number display
        })
        
        # Add current user to POS Profile
        pos_profile.append('applicable_for_users', {
            'user': frappe.session.user
        })
        
        pos_profile.insert()
        print(f"✅ Created POS Profile: {pos_profile.name}")
    
    print(f"📋 Company: {pos_profile.company}")
    print(f"👤 User: {frappe.session.user}")
    print(f"🏪 OEM Part Number Display: {'Enabled' if pos_profile.posa_show_oem_part_number_in_list else 'Disabled'}")
    print(f"🏢 Warehouse: {pos_profile.warehouse or 'Not set'}")
    print(f"🎯 Territory: {pos_profile.territory or 'Not set'}")
    print(f"💰 Price List: {pos_profile.selling_price_list or 'Not set'}")
    
    frappe.db.commit()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    frappe.destroy()

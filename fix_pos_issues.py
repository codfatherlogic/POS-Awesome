#!/usr/bin/env python3

import frappe
import sys

def fix_pos_issues():
    """Fix POS Awesome issues by enabling fields and checking data"""
    
    print("🔧 Fixing POS Awesome Issues")
    print("=" * 50)
    
    try:
        # Get POS Profile
        pos_profile = frappe.get_doc("POS Profile", "Paragon Polymer Products")
        
        # Enable all rate fields
        print("✅ Enabling rate fields in POS Profile...")
        pos_profile.show_last_purchase_rate_in_list = 1
        pos_profile.show_last_purchase_rate_in_cart = 1
        pos_profile.show_last_customer_rate_in_cart = 1
        
        # Enable OEM if field exists
        if hasattr(pos_profile, 'posa_show_oem_part_number_in_list'):
            pos_profile.posa_show_oem_part_number_in_list = 1
            print("✅ Enabled OEM display in list")
        
        # Save the profile
        pos_profile.save()
        frappe.db.commit()
        
        print("✅ POS Profile updated successfully!")
        
        # Test API functionality
        print("\n🧪 Testing API functionality...")
        
        # Import from items.py
        from posawesome.posawesome.api.items import get_items, get_last_purchase_rate
        
        # Test purchase rate function
        test_item = frappe.get_value("Item", {"disabled": 0}, "name")
        if test_item:
            purchase_rate = get_last_purchase_rate(test_item)
            print(f"   Purchase rate for {test_item}: {purchase_rate}")
        
        # Test items API with updated profile
        items_result = get_items(
            pos_profile=pos_profile.as_dict(),
            price_list="Standard Selling",
            item_group="",
            search_value="",
            customer="",
            limit=3
        )
        
        if items_result:
            item = items_result[0]
            print(f"   Sample item: {item.get('item_code')}")
            print(f"   Inc.Rate: {item.get('last_purchase_rate', 'Not found')}")
            print(f"   OEM: {item.get('custom_oem_part_number', 'Not found')}")
            
            # Check all expected fields
            expected_fields = ['last_purchase_rate', 'last_customer_rate', 'custom_oem_part_number']
            missing_fields = [f for f in expected_fields if f not in item]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print("   ✅ All expected fields present")
        
        print("\n🎯 Fix Complete!")
        print("📱 Please refresh the POS interface to see changes.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        frappe.init(site="pos")
        frappe.connect()
        fix_pos_issues()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

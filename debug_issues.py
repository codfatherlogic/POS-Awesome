#!/usr/bin/env python3

import frappe
import sys

def test_pos_issues():
    """Test and diagnose the current POS issues"""
    
    print("🔍 POS Awesome Issues Diagnosis")
    print("=" * 50)
    
    # 1. Check custom fields
    print("\n1. 📋 Custom Fields Status:")
    pos_profile_fields = frappe.get_all(
        "Custom Field",
        filters={"dt": "POS Profile"},
        fields=["fieldname", "label", "fieldtype"]
    )
    
    for field in pos_profile_fields:
        if "purchase_rate" in field.fieldname or "customer_rate" in field.fieldname:
            print(f"   ✅ {field.fieldname}: {field.label} ({field.fieldtype})")
    
    # 2. Check OEM field
    oem_field = frappe.db.exists('Custom Field', {'dt': 'Item', 'fieldname': 'custom_oem_part_number'})
    show_oem_field = frappe.db.exists('Custom Field', {'dt': 'POS Profile', 'fieldname': 'posa_show_oem_part_number_in_list'})
    
    print(f"\n2. 🔧 OEM Fields Status:")
    print(f"   OEM Part Number field: {'✅ Exists' if oem_field else '❌ Missing'}")
    print(f"   Show OEM in List field: {'✅ Exists' if show_oem_field else '❌ Missing'}")
    
    # 3. Check POS Profile settings
    pos_profile = frappe.get_doc("POS Profile", "Paragon Polymer Products")
    print(f"\n3. ⚙️  POS Profile Settings:")
    print(f"   Show Inc.Rate in List: {'✅ Enabled' if pos_profile.show_last_purchase_rate_in_list else '❌ Disabled'}")
    print(f"   Show Inc.Rate in Cart: {'✅ Enabled' if pos_profile.show_last_purchase_rate_in_cart else '❌ Disabled'}")
    print(f"   Show Cust.Rate in Cart: {'✅ Enabled' if pos_profile.show_last_customer_rate_in_cart else '❌ Disabled'}")
    print(f"   Show OEM in List: {'✅ Enabled' if getattr(pos_profile, 'posa_show_oem_part_number_in_list', 0) else '❌ Disabled'}")
    
    # 4. Test API functionality
    print(f"\n4. 🔌 API Testing:")
    try:
        from posawesome.posawesome.api.items import get_items, get_last_purchase_rate
        
        # Test purchase rate function
        test_item = frappe.get_value("Item", {"disabled": 0}, "name")
        if test_item:
            purchase_rate = get_last_purchase_rate(test_item)
            print(f"   Purchase rate for {test_item}: {purchase_rate}")
            
        # Test items API
        items_result = get_items(
            pos_profile=pos_profile.as_dict(),
            price_list="Standard Selling",
            item_group="",
            search_value="",
            customer="",
            limit=5
        )
        
        if items_result:
            item = items_result[0]
            print(f"   Sample item data keys: {list(item.keys())}")
            print(f"   Inc.Rate present: {'✅ Yes' if 'last_purchase_rate' in item else '❌ No'}")
            print(f"   OEM present: {'✅ Yes' if 'custom_oem_part_number' in item else '❌ No'}")
        
    except Exception as e:
        print(f"   ❌ API Error: {str(e)}")
    
    print(f"\n" + "=" * 50)
    print("🎯 Diagnosis Complete!")

if __name__ == "__main__":
    try:
        frappe.init(site="pos")
        frappe.connect()
        test_pos_issues()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

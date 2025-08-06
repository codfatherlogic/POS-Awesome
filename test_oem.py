import os
import sys
import frappe
import json

# Change to the correct directory
os.chdir('/Users/sammishthundiyil/frappe-bench-ai')

# Initialize Frappe
frappe.init(site='pos')
frappe.connect()

try:
    # Test OEM part number functionality
    print("🔍 Testing OEM Part Number functionality...")
    
    # Get POS Profile
    pos_profile = frappe.get_doc('POS Profile', 'Main POS Profile')
    print(f"📋 POS Profile: {pos_profile.name}")
    print(f"🏪 Show OEM in List: {pos_profile.posa_show_oem_part_number_in_list}")
    
    # Test item with OEM part number
    item_code = 'C0484'
    item = frappe.get_doc('Item', item_code)
    print(f"\n📦 Testing Item: {item.item_code}")
    print(f"📝 Item Name: {item.item_name}")
    print(f"🔧 OEM Part Number: {item.custom_oem_part_number}")
    
    # Test API call
    from posawesome.posawesome.api.items import get_items
    
    # Test normal search
    result = get_items(
        pos_profile=json.dumps(pos_profile.as_dict()),
        price_list='Standard Selling',
        search_value='C0484',
        limit=10
    )
    print(f"\n🔍 Search for 'C0484' found {len(result)} items")
    for item in result:
        if item['item_code'] == 'C0484':
            print(f"   ✅ Found item: {item['item_code']} - OEM: {item.get('custom_oem_part_number', 'Not found')}")
    
    # Test OEM search
    result_oem = get_items(
        pos_profile=json.dumps(pos_profile.as_dict()),
        price_list='Standard Selling',
        search_value='OME00101',
        limit=10
    )
    print(f"\n🔍 Search for OEM 'OME00101' found {len(result_oem)} items")
    for item in result_oem:
        if item.get('custom_oem_part_number') == 'OME00101':
            print(f"   ✅ Found by OEM: {item['item_code']} - OEM: {item.get('custom_oem_part_number')}")
    
    print("\n✅ Test completed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    frappe.destroy()

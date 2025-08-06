#!/usr/bin/env python3

import frappe
import json

def enable_pos_fields():
    """Enable the custom POS fields in the default POS Profile"""
    frappe.init("pos")
    frappe.connect()
    
    try:
        # Get the first available POS Profile
        pos_profiles = frappe.get_all("POS Profile", fields=["name"], limit=1)
        
        if not pos_profiles:
            print("❌ No POS Profile found!")
            return
            
        pos_profile_name = pos_profiles[0].name
        print(f"🏪 Updating POS Profile: {pos_profile_name}")
        
        # Get the POS Profile document
        pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
        
        # Enable the custom fields
        pos_profile.show_last_purchase_rate_in_list = 1
        pos_profile.show_last_purchase_rate_in_cart = 1
        pos_profile.show_last_customer_rate_in_cart = 1
        pos_profile.posa_show_oem_part_number_in_list = 1
        
        # Save the changes
        pos_profile.save()
        
        print("✅ Successfully enabled POS custom fields:")
        print(f"   📊 Show Inc.Rate in List: {'✓' if pos_profile.show_last_purchase_rate_in_list else '✗'}")
        print(f"   🛒 Show Inc.Rate in Cart: {'✓' if pos_profile.show_last_purchase_rate_in_cart else '✗'}")
        print(f"   👤 Show Cust.Rate in Cart: {'✓' if pos_profile.show_last_customer_rate_in_cart else '✗'}")
        print(f"   🔧 Show OEM in List: {'✓' if pos_profile.posa_show_oem_part_number_in_list else '✗'}")
        
        # Test purchase rate functionality
        print("\n🧪 Testing purchase rate functionality...")
        test_item_code = "7UP CAN 30x240ML SR 12121"  # From the screenshot
        
        try:
            # Test BIN valuation rate fetch
            warehouse = pos_profile.warehouse
            bin_data = frappe.db.get_value(
                "Bin",
                {"item_code": test_item_code, "warehouse": warehouse},
                ["valuation_rate", "actual_qty"],
                as_dict=True
            )
            
            if bin_data:
                print(f"   ✅ Found BIN data for {test_item_code}:")
                print(f"      Valuation Rate: {bin_data.valuation_rate}")
                print(f"      Actual Qty: {bin_data.actual_qty}")
            else:
                print(f"   ⚠️  No BIN data found for {test_item_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing purchase rate: {str(e)}")
        
        print(f"\n🎉 POS Profile '{pos_profile_name}' updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating POS Profile: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    enable_pos_fields()

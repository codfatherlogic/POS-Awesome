#!/usr/bin/env python3

import frappe

def check_custom_fields():
    # Initialize Frappe
    frappe.init(site='pos')
    frappe.connect()
    
    try:
        # Check custom fields on Item
        item_fields = frappe.get_all('Custom Field', 
                                   filters={'dt': 'Item'}, 
                                   fields=['fieldname', 'label'])
        print("Custom fields on Item:")
        for field in item_fields:
            print(f"  - {field.fieldname}: {field.label}")
        
        # Check custom fields on POS Profile
        pos_fields = frappe.get_all('Custom Field', 
                                  filters={'dt': 'POS Profile'}, 
                                  fields=['fieldname', 'label'])
        print("\nCustom fields on POS Profile:")
        for field in pos_fields:
            print(f"  - {field.fieldname}: {field.label}")
            
        # Check specifically for our fields
        oem_field = frappe.db.exists('Custom Field', {'dt': 'Item', 'fieldname': 'custom_oem_part_number'})
        show_oem_field = frappe.db.exists('Custom Field', {'dt': 'POS Profile', 'fieldname': 'posa_show_oem_part_number_in_list'})
        
        print(f"\nOEM Part Number field exists: {'Yes' if oem_field else 'No'}")
        print(f"Show OEM in list field exists: {'Yes' if show_oem_field else 'No'}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        frappe.destroy()

if __name__ == "__main__":
    check_custom_fields()

#!/usr/bin/env python3
"""
Test script for Smart Sync functionality
This script can be used to test if the Smart Sync detects various types of changes.
"""

import frappe
import json
from datetime import datetime, timedelta

def test_smart_sync_detection():
    """Test the Smart Sync change detection functionality"""
    
    # Connect to Frappe
    frappe.init(site='pos')
    frappe.connect()
    
    try:
        # Get a sample POS Profile
        pos_profiles = frappe.get_all("POS Profile", limit=1)
        if not pos_profiles:
            print("❌ No POS Profile found. Please create a POS Profile first.")
            return
        
        pos_profile_name = pos_profiles[0].name
        pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
        
        # Get selling price list from POS Profile
        price_list = pos_profile.selling_price_list
        
        print(f"🧪 Testing Smart Sync with POS Profile: {pos_profile_name}")
        print(f"📋 Price List: {price_list}")
        
        # Test 1: Check for changes with no timestamp (should return has_changes=False)
        print("\n📝 Test 1: Check with no timestamp")
        result = frappe.call(
            "posawesome.posawesome.api.items.check_for_changes",
            pos_profile=json.dumps(pos_profile.as_dict()),
            price_list=price_list,
            modified_after=None
        )
        print(f"Result: {result}")
        
        # Test 2: Check for changes in the last hour
        print("\n📝 Test 2: Check for changes in last hour")
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        result = frappe.call(
            "posawesome.posawesome.api.items.check_for_changes",
            pos_profile=json.dumps(pos_profile.as_dict()),
            price_list=price_list,
            modified_after=one_hour_ago
        )
        print(f"Result: {result}")
        
        # Test 3: Check for changes in the last 24 hours
        print("\n📝 Test 3: Check for changes in last 24 hours")
        one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        result = frappe.call(
            "posawesome.posawesome.api.items.check_for_changes",
            pos_profile=json.dumps(pos_profile.as_dict()),
            price_list=price_list,
            modified_after=one_day_ago
        )
        print(f"Result: {result}")
        
        if result.get('has_changes'):
            print(f"✅ Changes detected:")
            print(f"   📦 Items: {result.get('item_changes_count', 0)}")
            print(f"   💰 Prices: {result.get('price_changes_count', 0)}")
            print(f"   📏 UOMs: {result.get('uom_changes_count', 0)}")
            print(f"   📊 Barcodes: {result.get('barcode_changes_count', 0)}")
            print(f"   👥 Customers: {result.get('customer_changes_count', 0)}")
            print(f"   📁 Item Groups: {result.get('item_group_changes_count', 0)}")
            print(f"   📦 Batches: {result.get('batch_changes_count', 0)}")
            print(f"   🔢 Serial Numbers: {result.get('serial_changes_count', 0)}")
            print(f"   📈 Stock: {result.get('stock_changes_count', 0)}")
            
            changed_items = result.get('changed_items', [])
            if changed_items:
                print(f"   🔄 Changed Items: {changed_items[:5]}{'...' if len(changed_items) > 5 else ''}")
        else:
            print("ℹ️  No changes detected in the specified timeframe")
        
        print("\n✅ Smart Sync test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    test_smart_sync_detection()

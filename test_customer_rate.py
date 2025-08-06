#!/usr/bin/env python3

import requests
import json

# Test the customer rate API
def test_customer_rate():
    # API endpoint
    url = "http://localhost:8000/api/method/posawesome.posawesome.api.posapp.get_items"
    
    # Test data
    data = {
        "pos_profile": json.dumps({
            "name": "POS",
            "custom_show_last_custom_rate": 1,
            "warehouse": "Stores - AC",
            "currency": "USD"
        }),
        "customer": "Sammish",
        "search_value": "C0484",
        "limit": 1
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("message"):
                items = result["message"]
                if items:
                    item = items[0]
                    print(f"Item: {item.get('item_code')}")
                    print(f"Item Name: {item.get('item_name')}")
                    print(f"Rate: {item.get('rate')}")
                    print(f"Customer Rate: {item.get('customer_rate')}")
                    print(f"Last Customer Rate: {item.get('last_customer_rate')}")
                    return True
                else:
                    print("No items found")
            else:
                print(f"Error: {result.get('exc', 'Unknown error')}")
        else:
            print(f"HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Exception: {e}")
    
    return False

if __name__ == "__main__":
    print("Testing Customer Rate API...")
    test_customer_rate()

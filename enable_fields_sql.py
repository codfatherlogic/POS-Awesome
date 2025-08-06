#!/usr/bin/env python3

import subprocess
import json

# SQL commands to enable the fields
sql_commands = [
    "UPDATE `tabPOS Profile` SET show_last_purchase_rate_in_list = 1 WHERE name = (SELECT name FROM `tabPOS Profile` LIMIT 1);",
    "UPDATE `tabPOS Profile` SET show_last_purchase_rate_in_cart = 1 WHERE name = (SELECT name FROM `tabPOS Profile` LIMIT 1);", 
    "UPDATE `tabPOS Profile` SET show_last_customer_rate_in_cart = 1 WHERE name = (SELECT name FROM `tabPOS Profile` LIMIT 1);",
    "UPDATE `tabPOS Profile` SET posa_show_oem_part_number_in_list = 1 WHERE name = (SELECT name FROM `tabPOS Profile` LIMIT 1);"
]

for sql in sql_commands:
    try:
        cmd = f'bench --site pos mariadb -e "{sql}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Executed: {sql[:50]}...")
        else:
            print(f"❌ Failed: {sql[:50]}... - {result.stderr}")
    except Exception as e:
        print(f"❌ Error executing SQL: {e}")

print("\n🎉 POS Profile fields should now be enabled!")
print("👀 Please check the POS interface to confirm the changes.")

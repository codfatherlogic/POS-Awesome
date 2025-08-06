import frappe

@frappe.whitelist()
def test_customer_rate(customer, item_code):
    """Test function to check customer rate logic"""
    try:
        frappe.logger().info(f"Testing customer rate for: {customer}, {item_code}")
        
        # Check if customer exists
        customer_exists = frappe.db.exists("Customer", customer)
        frappe.logger().info(f"Customer exists: {customer_exists}")
        
        # Check if item exists
        item_exists = frappe.db.exists("Item", item_code)
        frappe.logger().info(f"Item exists: {item_exists}")
        
        # Try the SQL query
        result = frappe.db.sql("""
            SELECT sii.rate, si.name as invoice, si.posting_date
            FROM `tabSales Invoice Item` sii 
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent 
            WHERE si.customer = %s AND sii.item_code = %s AND si.docstatus = 1 
            ORDER BY si.posting_date DESC, si.creation DESC 
            LIMIT 1
        """, (customer, item_code), as_dict=True)
        
        frappe.logger().info(f"Query result: {result}")
        
        if result:
            rate = result[0].get("rate", 0)
            return {
                "success": True,
                "customer": customer,
                "item_code": item_code,
                "rate": rate,
                "invoice": result[0].get("invoice"),
                "posting_date": result[0].get("posting_date")
            }
        else:
            return {
                "success": False,
                "customer": customer,
                "item_code": item_code,
                "message": "No sales invoice found"
            }
            
    except Exception as e:
        frappe.logger().error(f"Error in test_customer_rate: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

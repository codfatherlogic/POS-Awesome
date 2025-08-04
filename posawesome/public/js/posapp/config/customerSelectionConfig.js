/**
 * Customer Selection Validation Configuration
 * Add this field to POS Profile DocType for configuration
 */

// Add this field to the POS Profile DocType via DocType customization:

const customerSelectionValidationField = {
    fieldname: "posa_require_customer_selection",
    fieldtype: "Check",
    label: "Require Customer Selection",
    description: "Require a customer to be selected before adding items to invoice",
    default: 1,
    insert_after: "customer"  // Add after the customer field
};

// Usage: Add this field to POS Profile DocType through customization
// frappe.customize_form("POS Profile", [customerSelectionValidationField]);

export { customerSelectionValidationField };

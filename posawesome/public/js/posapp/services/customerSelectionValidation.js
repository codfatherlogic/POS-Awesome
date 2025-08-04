/**
 * Simple Customer Selection Validation
 * Validates that a customer is selected before adding items
 */

class CustomerSelectionValidator {
    constructor() {
        this.isEnabled = true;
    }

    /**
     * Check if customer is selected before adding item
     * @param {Object} context - The invoice context with customer info
     * @returns {Object} - Validation result
     */
    validateCustomerSelected(context) {
        // Check if validation is enabled in POS Profile
        if (context.pos_profile && context.pos_profile.posa_require_customer_selection === 0) {
            return { isValid: true, message: null };
        }

        // Check if customer is selected and not the default one
        const defaultCustomer = context.pos_profile?.customer || "";
        const currentCustomer = context.customer || "";
        
        // Customer is valid if:
        // 1. A customer is selected AND
        // 2. It's not empty AND  
        // 3. It's different from the default customer (if any)
        const hasValidCustomer = currentCustomer && 
                                currentCustomer.trim() !== '' && 
                                (defaultCustomer === '' || currentCustomer !== defaultCustomer);

        if (!hasValidCustomer) {
            return {
                isValid: false,
                message: frappe._("Please select a customer before adding items to the invoice.")
            };
        }

        return { isValid: true, message: null };
    }

    /**
     * Show validation error message
     * @param {String} message - Error message to display
     * @param {Object} eventBus - Event bus for showing messages
     */
    showValidationError(message, eventBus) {
        if (eventBus) {
            eventBus.emit("show_message", {
                title: frappe._("Customer Required"),
                text: message,
                color: "warning",
                timeout: 5000
            });
        } else {
            frappe.show_alert({
                message: message,
                indicator: "orange"
            }, 5);
        }
    }
}

// Export singleton instance
export const customerSelectionValidator = new CustomerSelectionValidator();

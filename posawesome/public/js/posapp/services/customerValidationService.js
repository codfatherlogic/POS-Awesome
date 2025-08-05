/**
 * Customer Validation Service
 * Handles customer validation before item addition
 */

class CustomerValidationService {
	constructor() {
		this.validationEnabled = true;
		this.skipValidationForSession = false;
		this.eventBus = null;
	}

	// Initialize the service with event bus
	initialize(eventBus) {
		this.eventBus = eventBus;
		console.log("Customer Validation Service initialized");
	}

	// Check if validation should be performed
	shouldValidate(context) {
		// Skip if validation is disabled globally
		if (!this.validationEnabled) {
			return false;
		}

		// Skip if user chose "don't show again" for this session
		if (this.skipValidationForSession) {
			return false;
		}

		// Skip if no customer is selected (will be handled by existing validation)
		if (!context.customer) {
			return false;
		}

		// Skip if this is a return invoice (different workflow)
		if (context.isReturnInvoice) {
			return false;
		}

		// Skip if items already exist (validation only for first item)
		if (context.items && context.items.length > 0) {
			return false;
		}

		return true;
	}

	// Get customer information for validation
	async getCustomerInfo(customerName, context) {
		try {
			// First try to get from local customer info if available
			if (context.customer_info && context.customer_info.name === customerName) {
				return context.customer_info;
			}

			// Try to find in customers list
			if (context.customers && Array.isArray(context.customers)) {
				const customer = context.customers.find(c => 
					c.name === customerName || c.customer_name === customerName
				);
				if (customer) {
					return customer;
				}
			}

			// Fallback: create basic info object
			return {
				name: customerName,
				customer_name: customerName,
			};
		} catch (error) {
			console.error("Error getting customer info:", error);
			return {
				name: customerName,
				customer_name: customerName,
			};
		}
	}

	// Show validation dialog and get user confirmation
	async validateCustomerSelection(item, context) {
		if (!this.shouldValidate(context)) {
			return { confirmed: true, skipValidation: true };
		}

		if (!this.eventBus) {
			console.error("Customer validation service not initialized");
			return { confirmed: true, skipValidation: true };
		}

		try {
			const customerInfo = await this.getCustomerInfo(context.customer, context);
			const customerDisplayName = customerInfo.customer_name || customerInfo.name || context.customer;

			// Create a promise-based dialog request
			const result = await new Promise((resolve, reject) => {
				this.eventBus.emit("show_customer_validation_dialog", {
					item: item,
					customerName: customerDisplayName,
					customerInfo: customerInfo,
					resolve: resolve,
					reject: reject,
				});
			});

			// Handle "don't show again" option
			if (result.dontShowAgain) {
				this.skipValidationForSession = true;
				console.log("Customer validation disabled for this session");
			}

			return result;

		} catch (error) {
			console.error("Customer validation error:", error);
			// If validation fails, allow the operation to proceed
			return { confirmed: true, skipValidation: true, error: error };
		}
	}

	// Reset session settings (call when starting new invoice)
	resetSession() {
		this.skipValidationForSession = false;
	}

	// Enable/disable validation globally
	setValidationEnabled(enabled) {
		this.validationEnabled = enabled;
		console.log(`Customer validation ${enabled ? 'enabled' : 'disabled'}`);
	}

	// Get current validation status
	getValidationStatus() {
		return {
			enabled: this.validationEnabled,
			skipForSession: this.skipValidationForSession,
		};
	}
}

// Create singleton instance
const customerValidationService = new CustomerValidationService();

// Export for use in components
export { customerValidationService };

// Make it globally available for debugging
if (typeof window !== 'undefined') {
	window.customerValidationService = customerValidationService;
	
	// Add debugging commands
	window.debugCustomerValidation = () => {
		console.log("Customer Validation Service Status:", customerValidationService.getValidationStatus());
		console.log("Available commands:");
		console.log("- enableCustomerValidation() - Enable validation");
		console.log("- disableCustomerValidation() - Disable validation");
		console.log("- resetValidationSession() - Reset session settings");
		console.log("- getValidationStatus() - Get current status");
	};
	
	window.enableCustomerValidation = () => {
		customerValidationService.setValidationEnabled(true);
		console.log("Customer validation enabled");
	};
	
	window.disableCustomerValidation = () => {
		customerValidationService.setValidationEnabled(false);
		console.log("Customer validation disabled");
	};
	
	window.resetValidationSession = () => {
		customerValidationService.resetSession();
		console.log("Customer validation session reset");
	};
	
	window.getValidationStatus = () => {
		return customerValidationService.getValidationStatus();
	};
}

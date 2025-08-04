class t {
  constructor() {
    this.isEnabled = !0;
  }
  /**
   * Check if customer is selected before adding item
   * @param {Object} context - The invoice context with customer info
   * @returns {Object} - Validation result
   */
  validateCustomerSelected(e) {
    if (e.pos_profile && e.pos_profile.posa_require_customer_selection === 0)
      return { isValid: !0, message: null };
    const r = e.pos_profile?.customer || "", s = e.customer || "";
    return s && s.trim() !== "" && (r === "" || s !== r) ? { isValid: !0, message: null } : {
      isValid: !1,
      message: frappe._("Please select a customer before adding items to the invoice.")
    };
  }
  /**
   * Show validation error message
   * @param {String} message - Error message to display
   * @param {Object} eventBus - Event bus for showing messages
   */
  showValidationError(e, r) {
    r ? r.emit("show_message", {
      title: frappe._("Customer Required"),
      text: e,
      color: "warning",
      timeout: 5e3
    }) : frappe.show_alert({
      message: e,
      indicator: "orange"
    }, 5);
  }
}
const a = new t();
export {
  a as customerSelectionValidator
};

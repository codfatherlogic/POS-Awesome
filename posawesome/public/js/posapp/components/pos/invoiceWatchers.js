export default {
    // Watch for customer change and update related data
    customer() {
      this.close_payments();
      this.eventBus.emit("set_customer", this.customer);
      this.fetch_customer_details();
      this.fetch_customer_balance();
      this.set_delivery_charges();
    },
    // Watch for customer_info change and emit to edit form
    customer_info() {
      this.eventBus.emit("set_customer_info_to_edit", this.customer_info);
    },
    // Watch for expanded row change and update item detail
    expanded(data_value) {
      if (data_value.length > 0) {
        this.update_item_detail(data_value[0]);
      }
    },
    // Watch for discount offer name change and emit
    discount_percentage_offer_name() {
      this.eventBus.emit("update_discount_percentage_offer_name", {
        value: this.discount_percentage_offer_name,
      });
    },
    // Watch for items array changes (deep) and re-handle offers
    items: {
      deep: true,
      handler(items) {
        this.handelOffers();
        this.$forceUpdate();
      },
    },
    // Watch for invoice type change and emit
    invoiceType() {
      this.eventBus.emit("update_invoice_type", this.invoiceType);
    },
    // Watch for additional discount and update percentage accordingly
    additional_discount() {
      if (!this.additional_discount || this.additional_discount == 0) {
        this.additional_discount_percentage = 0;
      } else if (this.pos_profile.posa_use_percentage_discount) {
        // Prevent division by zero which causes NaN
        if (this.Total && this.Total !== 0) {
          this.additional_discount_percentage =
            (this.additional_discount / this.Total) * 100;
        } else {
          this.additional_discount_percentage = 0;
        }
      } else {
        this.additional_discount_percentage = 0;
      }
    },
    // Keep display date in sync with posting_date
    posting_date: {
      handler(newVal) {
        this.posting_date_display = this.formatDateForDisplay(newVal);
      },
      immediate: true,
    },
    // Update posting_date when user changes the display value
    posting_date_display(newVal) {
      this.posting_date = this.formatDateForBackend(newVal);
    },

    selected_price_list(newVal) {
      const price_list = newVal === this.pos_profile.selling_price_list ? null : newVal;
      this.eventBus.emit("update_customer_price_list", price_list);
    },
};

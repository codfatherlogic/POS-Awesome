# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

import json
from typing import Dict, List

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.batch.batch import get_batch_no  # This should be from erpnext directly
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, money_in_words, nowdate
from frappe.utils.background_jobs import enqueue

from posawesome.posawesome.api.payments import redeeming_customer_credit  # Updated import
from posawesome.posawesome.api.utilities import (
    ensure_child_doctype,
    set_batch_nos_for_bundels,
)  # Updated imports


@frappe.whitelist()
def validate_return_items(original_invoice_name, return_items):
    """
    Ensure that return items do not exceed the quantity from the original invoice.
    """
    original_invoice = frappe.get_doc("Sales Invoice", original_invoice_name)
    original_item_qty = {}

    for item in original_invoice.items:
        original_item_qty[item.item_code] = original_item_qty.get(item.item_code, 0) + item.qty

    returned_items = frappe.get_all(
        "Sales Invoice",
        filters={
            "return_against": original_invoice_name,
            "docstatus": 1,
            "is_return": 1
        },
        fields=["name"]
    )

    for returned_invoice in returned_items:
        ret_doc = frappe.get_doc("Sales Invoice", returned_invoice.name)
        for item in ret_doc.items:
            if item.item_code in original_item_qty:
                original_item_qty[item.item_code] -= abs(item.qty)

    for item in return_items:
        item_code = item.get("item_code")
        return_qty = abs(item.get("qty", 0))
        if item_code in original_item_qty and return_qty > original_item_qty[item_code]:
            return {
                "valid": False,
                "message": _("You are trying to return more quantity for item {0} than was sold.").format(item_code),
            }

    return {"valid": True}


@frappe.whitelist()
def update_invoice(data):
    data = json.loads(data)
    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.update(data)
    else:
        invoice_doc = frappe.get_doc(data)

    # Set currency from data before set_missing_values
    # Validate return items if this is a return invoice
    if (data.get("is_return") or invoice_doc.is_return) and invoice_doc.get("return_against"):
        validation = validate_return_items(invoice_doc.return_against, [d.as_dict() for d in invoice_doc.items])
        if not validation.get("valid"):
            frappe.throw(validation.get("message"))
    selected_currency = data.get("currency")
    price_list_currency = data.get("price_list_currency")

    # Set missing values first
    invoice_doc.set_missing_values()

    # Ensure selected currency is preserved after set_missing_values
    if selected_currency:
        invoice_doc.currency = selected_currency
        # Get default conversion rate from ERPNext if currency is different from company currency
        base_currency = price_list_currency or frappe.get_cached_value(
            "Company", invoice_doc.company, "default_currency"
        )

        if invoice_doc.currency != base_currency:
            # Get exchange rate from selected currency to base currency
            exchange_rate = get_exchange_rate(
                invoice_doc.currency,
                base_currency,
                invoice_doc.posting_date
            )
            invoice_doc.conversion_rate = exchange_rate
            invoice_doc.plc_conversion_rate = exchange_rate
            invoice_doc.price_list_currency = price_list_currency or selected_currency

            # Update rates and amounts for all items using multiplication
            for item in invoice_doc.items:
                if item.price_list_rate:
                    # If exchange rate is 285 PKR = 1 USD
                    # To convert USD to PKR: multiply by exchange rate
                    # Example: 0.35 USD * 285 = 100 PKR
                    item.base_price_list_rate = flt(item.price_list_rate * exchange_rate, item.precision("base_price_list_rate"))
                if item.rate:
                    item.base_rate = flt(item.rate * exchange_rate, item.precision("base_rate"))
                if item.amount:
                    item.base_amount = flt(item.amount * exchange_rate, item.precision("base_amount"))

            # Update payment amounts
            for payment in invoice_doc.payments:
                payment.base_amount = flt(payment.amount * exchange_rate, payment.precision("base_amount"))

            # Update invoice level amounts
            invoice_doc.base_total = flt(invoice_doc.total * exchange_rate, invoice_doc.precision("base_total"))
            invoice_doc.base_net_total = flt(invoice_doc.net_total * exchange_rate, invoice_doc.precision("base_net_total"))
            invoice_doc.base_grand_total = flt(invoice_doc.grand_total * exchange_rate, invoice_doc.precision("base_grand_total"))
            invoice_doc.base_rounded_total = flt(invoice_doc.rounded_total * exchange_rate, invoice_doc.precision("base_rounded_total"))
            invoice_doc.base_in_words = money_in_words(invoice_doc.base_rounded_total, base_currency)

            # Update data to be sent back to frontend
            data["conversion_rate"] = exchange_rate
            data["plc_conversion_rate"] = exchange_rate

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.docstatus = 0
    invoice_doc.save()

    # Return both the invoice doc and the updated data
    response = invoice_doc.as_dict()
    response["conversion_rate"] = invoice_doc.conversion_rate
    response["plc_conversion_rate"] = invoice_doc.conversion_rate
    return response


@frappe.whitelist()
def submit_invoice(invoice, data):
    data = json.loads(data)
    invoice = json.loads(invoice)
    invoice_name = invoice.get("name")
    if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
        created = update_invoice(json.dumps(invoice))
        invoice_name = created.get("name")
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
    else:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
        invoice_doc.update(invoice)
    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]
    if len(mop_cash_list) > 0:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {
            "account": frappe.get_value(
                "Company", invoice_doc.company, "default_cash_account"
            )
        }

    # Update remarks with items details
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    # Add the grand total at the end of remarks
    grand_total = f"\nGrand Total: {invoice_doc.grand_total}"
    items.append(grand_total)

    invoice_doc.remarks = "\n".join(items)

    # creating advance payment
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "mode_of_payment": "Cash",
                "paid_to": cash_account["account"],
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": invoice_doc.get("customer"),
                "paid_amount": invoice_doc.get("credit_change"),
                "received_amount": invoice_doc.get("credit_change"),
                "company": invoice_doc.get("company"),
            }
        )

        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # calculating cash
    total_cash = 0
    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

    is_payment_entry = 0
    if data.get("redeemed_customer_credit"):
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                advance_payment = {
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                }

                advance_row = invoice_doc.append("advances", {})
                advance_row.update(advance_payment)
                ensure_child_doctype(invoice_doc, "advances", "Sales Invoice Advance")
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    # if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
    #     set_batch_nos(invoice_doc, "warehouse", throw=True)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    invoice_doc.save()

    if data.get("due_date"):
        frappe.db.set_value(
            "Sales Invoice",
            invoice_doc.name,
            "due_date",
            data.get("due_date"),
            update_modified=False,
        )

    if frappe.get_value(
        "POS Profile",
        invoice_doc.pos_profile,
        "posa_allow_submissions_in_background_job",
    ):
        invoices_list = frappe.get_all(
            "Sales Invoice",
            filters={
                "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                "docstatus": 0,
                "posa_is_printed": 1,
            },
        )
        for invoice in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": invoice.name,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        invoice_doc.submit()
        redeeming_customer_credit(
            invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
        )

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}


def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    invoice_doc = kwargs.get("invoice_doc")
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc("Sales Invoice", invoice)

    # Update remarks with items details for background job
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    # Add the grand total at the end of remarks
    grand_total = f"\nGrand Total: {invoice_doc.grand_total}"
    items.append(grand_total)

    invoice_doc.remarks = "\n".join(items)
    invoice_doc.save()

    invoice_doc.submit()
    redeeming_customer_credit(
        invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
    )


@frappe.whitelist()
def delete_invoice(invoice):
    if frappe.get_value("Sales Invoice", invoice, "posa_is_printed"):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))
    frappe.delete_doc("Sales Invoice", invoice, force=1)
    return _("Invoice {0} Deleted").format(invoice)


@frappe.whitelist()
def get_draft_invoices(pos_opening_shift):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 0,
            "posa_is_printed": 0,
        },
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc("Sales Invoice", invoice["name"]))
    return data


@frappe.whitelist()
def search_invoices_for_return(invoice_name, company, customer_name=None, customer_id=None,
                               mobile_no=None, tax_id=None, from_date=None, to_date=None,
                               min_amount=None, max_amount=None, page=1):
    """
    Search for invoices that can be returned with separate customer search fields and pagination
    
    Args:
        invoice_name: Invoice ID to search for
        company: Company to search in
        customer_name: Customer name to search for
        customer_id: Customer ID to search for
        mobile_no: Mobile number to search for
        tax_id: Tax ID to search for
        from_date: Start date for filtering
        to_date: End date for filtering
        min_amount: Minimum invoice amount to filter by
        max_amount: Maximum invoice amount to filter by
        page: Page number for pagination (starts from 1)
    
    Returns:
        Dictionary with:
            - invoices: List of invoice documents
            - has_more: Boolean indicating if there are more invoices to load
    """
    # Start with base filters
    filters = {
        "company": company,
        "docstatus": 1,
        "is_return": 0,
    }

    # Convert page to integer if it's a string
    if page and isinstance(page, str):
        page = int(page)
    else:
        page = 1  # Default to page 1

    # Items per page - can be adjusted based on performance requirements
    page_length = 100
    start = (page - 1) * page_length

    # Add invoice name filter if provided
    if invoice_name:
        filters["name"] = ["like", f"%{invoice_name}%"]

    # Add date range filters if provided
    if from_date:
        filters["posting_date"] = [">=", from_date]

    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = ["between", [from_date, to_date]]
        else:
            filters["posting_date"] = ["<=", to_date]

    # Add amount filters if provided
    if min_amount:
        filters["grand_total"] = [">=", float(min_amount)]

    if max_amount:
        if "grand_total" in filters:
            # If min_amount was already set, change to between
            filters["grand_total"] = ["between", [float(min_amount), float(max_amount)]]
        else:
            filters["grand_total"] = ["<=", float(max_amount)]

    # If any customer search criteria is provided, find matching customers
    customer_ids = []
    if customer_name or customer_id or mobile_no or tax_id:
        conditions = []
        params = {}

        if customer_name:
            conditions.append("customer_name LIKE %(customer_name)s")
            params["customer_name"] = f"%{customer_name}%"

        if customer_id:
            conditions.append("name LIKE %(customer_id)s")
            params["customer_id"] = f"%{customer_id}%"

        if mobile_no:
            conditions.append("mobile_no LIKE %(mobile_no)s")
            params["mobile_no"] = f"%{mobile_no}%"

        if tax_id:
            conditions.append("tax_id LIKE %(tax_id)s")
            params["tax_id"] = f"%{tax_id}%"

        # Build the WHERE clause for the query
        where_clause = " OR ".join(conditions)
        customer_query = f"""
            SELECT name 
            FROM `tabCustomer`
            WHERE {where_clause}
            LIMIT 100
        """

        customers = frappe.db.sql(customer_query, params, as_dict=True)
        customer_ids = [c.name for c in customers]

        # If we found matching customers, add them to the filter
        if customer_ids:
            filters["customer"] = ["in", customer_ids]
        # If customer search criteria provided but no matches found, return empty
        elif any([customer_name, customer_id, mobile_no, tax_id]):
            return {"invoices": [], "has_more": False}

    # Count total invoices matching the criteria (for has_more flag)
    total_count_query = frappe.get_list(
        "Sales Invoice",
        filters=filters,
        fields=["count(name) as total_count"],
        as_list=False,
    )
    total_count = total_count_query[0].total_count if total_count_query else 0

    # Get invoices matching all criteria with pagination
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters=filters,
        fields=["name"],
        limit_start=start,
        limit_page_length=page_length,
        order_by="posting_date desc, name desc",
    )

    # Process and return the results
    data = []

    # Process invoices and check for returns
    for invoice in invoices_list:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice.name)

        # Check if any items have already been returned
        has_returns = frappe.get_all(
            "Sales Invoice",
            filters={
                "return_against": invoice.name,
                "docstatus": 1
            },
            fields=["name"]
        )

        if has_returns:
            # Calculate returned quantity per item_code
            returned_qty = {}
            for ret_inv in has_returns:
                ret_doc = frappe.get_doc("Sales Invoice", ret_inv.name)
                for item in ret_doc.items:
                    returned_qty[item.item_code] = (
                        returned_qty.get(item.item_code, 0) + abs(item.qty)
                    )

            # Filter items with remaining qty
            filtered_items = []
            for item in invoice_doc.items:
                remaining_qty = item.qty - returned_qty.get(item.item_code, 0)
                if remaining_qty > 0:
                    new_item = item.as_dict().copy()
                    new_item["qty"] = remaining_qty
                    new_item["amount"] = remaining_qty * item.rate
                    if item.get("stock_qty"):
                        new_item["stock_qty"] = (
                            item.stock_qty / item.qty * remaining_qty
                            if item.qty
                            else remaining_qty
                        )
                    filtered_items.append(frappe._dict(new_item))

            if filtered_items:
                # Create a copy of invoice with filtered items
                filtered_invoice = frappe.get_doc("Sales Invoice", invoice.name)
                filtered_invoice.items = filtered_items
                data.append(filtered_invoice)
        else:
            data.append(invoice_doc)

    # Check if there are more results
    has_more = (start + page_length) < total_count

    return {
        "invoices": data,
        "has_more": has_more
    }


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    sales_invoice = make_sales_invoice(sales_order, ignore_permissions=True)
    sales_invoice.save()
    return sales_invoice


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    frappe.delete_doc("Sales Invoice", sales_invoice)


@frappe.whitelist()
def get_sales_invoice_child_table(sales_invoice, sales_invoice_item):
    parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    child_doc = frappe.get_doc(
        "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
    )
    return child_doc


@frappe.whitelist()
def update_invoice_from_order(data):
     data = json.loads(data)
     invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
     invoice_doc.update(data)
     invoice_doc.save()
     return invoice_doc


@frappe.whitelist()
def get_available_currencies():
    """Get list of available currencies from ERPNext"""
    return frappe.get_all("Currency", fields=["name", "currency_name"],
                         filters={"enabled": 1}, order_by="currency_name")


@frappe.whitelist()
def fetch_exchange_rate(currency: str, company: str, posting_date: str = None):
    """Return exchange rate for the given currency against company's currency."""
    posting_date = posting_date or nowdate()
    company_currency = frappe.get_cached_value("Company", company, "default_currency")
    exchange_rate = get_exchange_rate(currency, company_currency, posting_date)
    return exchange_rate


@frappe.whitelist()
def fetch_exchange_rate_pair(from_currency: str, to_currency: str, posting_date: str = None):
    """Return exchange rate between two currencies."""
    posting_date = posting_date or nowdate()
    return get_exchange_rate(from_currency, to_currency, posting_date)


@frappe.whitelist()
def get_price_list_currency(price_list: str) -> str:
    """Return the currency of the given Price List."""
    if not price_list:
        return None
    return frappe.db.get_value("Price List", price_list, "currency")

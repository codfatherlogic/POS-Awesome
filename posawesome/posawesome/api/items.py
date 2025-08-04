# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups
from erpnext.stock.doctype.batch.batch import (
	get_batch_no,
	get_batch_qty,
)
from erpnext.stock.get_item_details import get_item_details
from frappe import _
from frappe.utils import cstr, flt, nowdate
from frappe.utils.background_jobs import enqueue
from frappe.utils.caching import redis_cache


def get_seearch_items_conditions(item_code, serial_no, batch_no, barcode):
	"""Build item search conditions safely."""
	# Gracefully handle missing item_code values to avoid TypeErrors
	item_code = item_code or ""

	if serial_no or batch_no or barcode:
		return f" and name = {frappe.db.escape(item_code)}"

	return """ and (name like {item_code} or item_name like {item_code})""".format(
		item_code=frappe.db.escape("%" + item_code + "%")
	)


def get_item_group_condition(pos_profile):
	cond = " and 1=1"
	item_groups = get_item_groups(pos_profile)
	if item_groups:
		cond = " and item_group in ({})".format(", ".join(["%s"] * len(item_groups)))

	return cond % tuple(item_groups)


def get_stock_availability(item_code, warehouse):
	"""Get the latest stock quantity for an item in a specific warehouse."""
	try:
		# Use SQL query to get the latest stock ledger entry
		result = frappe.db.sql("""
			SELECT qty_after_transaction 
			FROM `tabStock Ledger Entry` 
			WHERE item_code = %s 
			AND warehouse = %s 
			AND is_cancelled = 0
			ORDER BY posting_date DESC, posting_time DESC, creation DESC
			LIMIT 1
		""", (item_code, warehouse))
		
		if result and len(result) > 0:
			actual_qty = flt(result[0][0] or 0.0)
		else:
			actual_qty = 0.0
			
		frappe.logger().debug(f"Stock availability for {item_code} in {warehouse}: {actual_qty}")
		return actual_qty
		
	except Exception as e:
		frappe.logger().error(f"Error getting stock availability for {item_code} in {warehouse}: {str(e)}")
		return 0.0


@frappe.whitelist()
def get_items(
	pos_profile,
	price_list=None,
	item_group="",
	search_value="",
	customer=None,
	limit=None,
	offset=None,
	modified_after=None,
):
	_pos_profile = json.loads(pos_profile)
	use_price_list = _pos_profile.get("posa_use_server_cache")

	@redis_cache(ttl=60)
	def __get_items(
		pos_profile,
		price_list,
		item_group,
		search_value,
		customer=None,
		limit=None,
		offset=None,
		modified_after=None,
	):
		return _get_items(
		        pos_profile,
		        price_list,
		        item_group,
		        search_value,
		        customer,
		        limit,
		        offset,
		        modified_after,
		)

	def _get_items(
		pos_profile,
		price_list,
		item_group,
		search_value,
		customer=None,
		limit=None,
		offset=None,
		modified_after=None,
	):
		pos_profile = json.loads(pos_profile)
		condition = ""

		# Clear quantity cache to ensure fresh values on each search
		try:
			if hasattr(frappe.local.cache, "delete_key"):
				frappe.local.cache.delete_key("bin_qty_cache")
			elif frappe.cache().get_value("bin_qty_cache"):
				frappe.cache().delete_value("bin_qty_cache")
		except Exception as e:
			frappe.log_error(f"Error clearing bin_qty_cache: {e!s}", "POS Awesome")

		today = nowdate()
		warehouse = pos_profile.get("warehouse")
		use_limit_search = pos_profile.get("pose_use_limit_search")
		search_serial_no = pos_profile.get("posa_search_serial_no")
		search_batch_no = pos_profile.get("posa_search_batch_no")
		posa_show_template_items = pos_profile.get("posa_show_template_items")
		posa_display_items_in_stock = pos_profile.get("posa_display_items_in_stock")
		search_limit = 0

		if not price_list:
			price_list = pos_profile.get("selling_price_list")

		limit_clause = ""

		def _to_positive_int(value):
			"""Convert the input to a non-negative integer if possible."""
			try:
				ivalue = int(value)
				return ivalue if ivalue >= 0 else None
			except (TypeError, ValueError):
				return None

		limit = _to_positive_int(limit)
		offset = _to_positive_int(offset)

		if limit is not None:
			limit_clause = f" LIMIT {limit}"
			if offset:
				limit_clause += f" OFFSET {offset}"

		condition += get_item_group_condition(pos_profile.get("name"))

		if use_limit_search and limit is None:
			search_limit = pos_profile.get("posa_search_limit") or 500
			data = {}
			if search_value:
				data = search_serial_or_batch_or_barcode_number(search_value, search_serial_no)

			item_code = data.get("item_code") if data.get("item_code") else search_value
			serial_no = data.get("serial_no") if data.get("serial_no") else ""
			batch_no = data.get("batch_no") if data.get("batch_no") else ""
			barcode = data.get("barcode") if data.get("barcode") else ""

			condition += get_seearch_items_conditions(item_code, serial_no, batch_no, barcode)
			if item_group:
				# Escape item_group to avoid SQL errors with special characters
				safe_item_group = frappe.db.escape("%" + item_group + "%")
				condition += f" AND item_group like {safe_item_group}"

			# Always apply a search limit when limit search is enabled
			limit_clause = f" LIMIT {search_limit}"

			# If force reload is enabled and the user is explicitly searching,
			# remove the limit to return all matching items
			if pos_profile.get("posa_force_reload_items") and search_value:
				limit_clause = ""

		if not posa_show_template_items:
			condition += " AND has_variants = 0"

		result = []

		# Build ORM filters
		filters = {"disabled": 0, "is_sales_item": 1, "is_fixed_asset": 0}
		if modified_after:
			filters["modified"] = [">", modified_after]

		# Add item group filter
		item_groups = get_item_groups(pos_profile.get("name"))
		item_groups = [g.strip("'") for g in item_groups]
		if item_groups:
			filters["item_group"] = ["in", item_groups]

		# Add search conditions
		or_filters = []
		if use_limit_search and search_value:
			data = search_serial_or_batch_or_barcode_number(search_value, search_serial_no)
			item_code = data.get("item_code") if data.get("item_code") else search_value

			or_filters = [
				["name", "like", f"%{item_code}%"],
				["item_name", "like", f"%{item_code}%"],
			]

			# Check for exact barcode match
			if data.get("item_code"):
				filters["name"] = data.get("item_code")
				or_filters = []

		if item_group and item_group.upper() != "ALL":
			filters["item_group"] = ["like", f"%{item_group}%"]

		if not posa_show_template_items:
			filters["has_variants"] = 0

		# Determine limit
		limit_page_length = None
		limit_start = None

		if limit is not None:
			limit_page_length = limit
			if offset:
				limit_start = offset
		elif use_limit_search:
			limit_page_length = search_limit
			if pos_profile.get("posa_force_reload_items") and search_value:
				limit_page_length = None

		items_data = frappe.get_all(
			"Item",
			filters=filters,
			or_filters=or_filters if or_filters else None,
			fields=[
				"name as item_code",
				"item_name",
				"description",
				"stock_uom",
				"image",
				"is_stock_item",
				"has_variants",
				"variant_of",
				"item_group",
				"idx",
				"has_batch_no",
				"has_serial_no",
				"max_discount",
				"brand",
			],
			limit_start=limit_start,
			limit_page_length=limit_page_length,
			order_by="item_name asc",
		)

		if items_data:
			items = [d.item_code for d in items_data]
			price_list_currency = frappe.db.get_value("Price List", price_list, "currency")
			item_prices_data = frappe.get_all(
				"Item Price",
				fields=["item_code", "price_list_rate", "currency", "uom"],
				filters={
					"price_list": price_list,
					"item_code": ["in", items],
					"currency": price_list_currency or pos_profile.get("currency"),
					"selling": 1,
					"valid_from": ["<=", today],
					"customer": ["in", ["", None, customer]],
				},
				or_filters=[
					["valid_upto", ">=", today],
					["valid_upto", "in", ["", None]],
				],
				order_by="valid_from ASC, valid_upto DESC",
			)

			item_prices = {}
			for d in item_prices_data:
				item_prices.setdefault(d.item_code, {})
				item_prices[d.item_code][d.get("uom") or "None"] = d

			for item in items_data:
				item_code = item.item_code
				item_price = {}
				if item_prices.get(item_code):
					item_price = (
						item_prices.get(item_code).get(item.stock_uom)
						or item_prices.get(item_code).get("None")
						or {}
					)
				item_barcode = frappe.get_all(
					"Item Barcode",
					filters={"parent": item_code},
					fields=["barcode", "posa_uom"],
				)
				batch_no_data = []
				if search_batch_no or item.has_batch_no:
					batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
					if batch_list:
						for batch in batch_list:
							if batch.qty > 0 and batch.batch_no:
								batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
								if (
									str(batch_doc.expiry_date) > str(today)
									or batch_doc.expiry_date in ["", None]
								) and batch_doc.disabled == 0:
									batch_no_data.append(
										{
											"batch_no": batch.batch_no,
											"batch_qty": batch.qty,
											"expiry_date": batch_doc.expiry_date,
											"batch_price": batch_doc.posa_batch_price,
											"manufacturing_date": batch_doc.manufacturing_date,
										}
									)
				serial_no_data = []
				if search_serial_no or item.has_serial_no:
					serial_no_data = frappe.get_all(
						"Serial No",
						filters={
							"item_code": item_code,
							"status": "Active",
							"warehouse": warehouse,
						},
						fields=["name as serial_no"],
					)
				# Fetch UOM conversion details for the item
				uoms = frappe.get_all(
					"UOM Conversion Detail",
					filters={"parent": item_code},
					fields=["uom", "conversion_factor"],
				)
				stock_uom = item.stock_uom
				if stock_uom and not any(u.get("uom") == stock_uom for u in uoms):
					uoms.append({"uom": stock_uom, "conversion_factor": 1.0})
				item_stock_qty = 0
				if pos_profile.get("posa_display_items_in_stock") or use_limit_search:
					item_stock_qty = get_stock_availability(item_code, pos_profile.get("warehouse"))
				attributes = ""
				if pos_profile.get("posa_show_template_items") and item.has_variants:
					attributes = get_item_attributes(item.item_code)
				item_attributes = ""
				if pos_profile.get("posa_show_template_items") and item.variant_of:
					item_attributes = frappe.get_all(
						"Item Variant Attribute",
						fields=["attribute", "attribute_value"],
						filters={"parent": item.item_code, "parentfield": "attributes"},
					)
				if posa_display_items_in_stock and (not item_stock_qty or item_stock_qty < 0):
					pass
				else:
					row = {}
					row.update(item)
					row.update(
						{
							"rate": item_price.get("price_list_rate") or 0,
							"currency": item_price.get("currency")
							or price_list_currency
							or pos_profile.get("currency"),
							"item_barcode": item_barcode or [],
							"actual_qty": item_stock_qty or 0,
							"serial_no_data": serial_no_data or [],
							"batch_no_data": batch_no_data or [],
							"attributes": attributes or "",
							"item_attributes": item_attributes or "",
							"item_uoms": uoms or [],
						}
					)
					result.append(row)
		return result

	if use_price_list:
		return __get_items(
		        pos_profile,
		        price_list,
		        item_group,
		        search_value,
		        customer,
		        limit,
		        offset,
		        modified_after,
		)
	else:
		return _get_items(
		        pos_profile,
		        price_list,
		        item_group,
		        search_value,
		        customer,
		        limit,
		        offset,
		        modified_after,
		)


@frappe.whitelist()
def get_items_groups():
	return frappe.db.sql(
		"""select name from `tabItem Group`
	    where is_group = 0 order by name limit 500""",
		as_dict=1,
	)


@frappe.whitelist()
def get_item_variants(pos_profile, parent_item_code, price_list=None, customer=None):
	"""Return variants of an item along with attribute metadata."""
	pos_profile = json.loads(pos_profile)
	price_list = price_list or pos_profile.get("selling_price_list")

	fields = [
		"name as item_code",
		"item_name",
		"description",
		"stock_uom",
		"image",
		"is_stock_item",
		"has_variants",
		"variant_of",
		"item_group",
		"idx",
		"has_batch_no",
		"has_serial_no",
		"max_discount",
		"brand",
	]

	items_data = frappe.get_all(
		"Item",
		filters={"variant_of": parent_item_code, "disabled": 0},
		fields=fields,
		order_by="item_name asc",
	)

	if not items_data:
		return {"variants": [], "attributes_meta": {}}

	details = get_items_details(
		json.dumps(pos_profile),
		json.dumps(items_data),
		price_list=price_list,
	)

	detail_map = {d["item_code"]: d for d in details}
	result = []
	for item in items_data:
		item_barcode = frappe.get_all(
			"Item Barcode",
			filters={"parent": item["item_code"]},
			fields=["barcode", "posa_uom"],
		)
		item["item_barcode"] = item_barcode or []
		if detail_map.get(item["item_code"]):
			item.update(detail_map[item["item_code"]])
		result.append(item)

	# --------------------------
	# Build attributes meta *and* per-item attribute list
	# --------------------------
	attr_rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", [d["item_code"] for d in items_data]]},
		fields=["parent", "attribute", "attribute_value"],
	)

	from collections import defaultdict

	attributes_meta: dict[str, set] = defaultdict(set)
	item_attr_map: dict[str, list] = defaultdict(list)

	for row in attr_rows:
		attributes_meta[row.attribute].add(row.attribute_value)
		item_attr_map[row.parent].append({"attribute": row.attribute, "attribute_value": row.attribute_value})

	attributes_meta = {k: sorted(v) for k, v in attributes_meta.items()}

	for item in result:
		item["item_attributes"] = item_attr_map.get(item["item_code"], [])

	# Ensure attributes_meta is always a dictionary
	return {"variants": result, "attributes_meta": attributes_meta or {}}


@frappe.whitelist()
def get_items_details(pos_profile, items_data, price_list=None):
	pos_profile = json.loads(pos_profile)
	items_data = json.loads(items_data)
	warehouse = pos_profile.get("warehouse")
	company = (
		pos_profile.get("company")
		or frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
	)
	result = []

	if items_data:
		for item in items_data:
			item_code = item.get("item_code")
			if item_code:
				if item.get("has_variants"):
					# Skip template items to avoid ValidationError
					continue
				item_detail = get_item_detail(
					json.dumps(item),
						warehouse=warehouse,
						price_list=price_list or pos_profile.get("selling_price_list"),
						company=company,
					)
				if item_detail:
					result.append(item_detail)

	return result


@frappe.whitelist()
def get_item_detail(item, doc=None, warehouse=None, price_list=None, company=None):
	item = json.loads(item)
	
	# Parse doc if it's passed as JSON string
	if doc and isinstance(doc, str):
		try:
			doc = json.loads(doc)
		except (json.JSONDecodeError, TypeError):
			doc = None
	
	# Ensure doc is a frappe._dict if it's a regular dict
	if doc and isinstance(doc, dict) and not isinstance(doc, frappe._dict):
		doc = frappe._dict(doc)
	
	today = nowdate()
	item_code = item.get("item_code")
	batch_no_data = []
	serial_no_data = []
	if warehouse and item.get("has_batch_no"):
		batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
		if batch_list:
			for batch in batch_list:
				if batch.qty > 0 and batch.batch_no:
					batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
					if (
						str(batch_doc.expiry_date) > str(today) or batch_doc.expiry_date in ["", None]
					) and batch_doc.disabled == 0:
						batch_no_data.append(
							{
								"batch_no": batch.batch_no,
								"batch_qty": batch.qty,
								"expiry_date": batch_doc.expiry_date,
								"batch_price": batch_doc.posa_batch_price,
								"manufacturing_date": batch_doc.manufacturing_date,
							}
						)
	if warehouse and item.get("has_serial_no"):
		serial_no_data = frappe.get_all(
			"Serial No",
			filters={
				"item_code": item_code,
				"status": "Active",
				"warehouse": warehouse,
			},
			fields=["name as serial_no"],
		)

	item["selling_price_list"] = price_list

	# Determine if multi-currency is enabled on the POS Profile
	allow_multi_currency = False
	if item.get("pos_profile"):
		allow_multi_currency = (
			frappe.db.get_value("POS Profile", item.get("pos_profile"), "posa_allow_multi_currency") or 0
		)

	# Ensure conversion rate exists when price list currency differs from
	# company currency to avoid ValidationError from ERPNext. Also provide
	# sensible defaults when price list or currency is missing.
	if company:
		company_currency = frappe.db.get_value("Company", company, "default_currency")
		price_list_currency = company_currency
		if price_list:
			price_list_currency = (
				frappe.db.get_value("Price List", price_list, "currency") or company_currency
			)

		exchange_rate = 1
		if price_list_currency != company_currency and allow_multi_currency:
			from erpnext.setup.utils import get_exchange_rate

			try:
				exchange_rate = get_exchange_rate(price_list_currency, company_currency, today)
			except Exception:
				frappe.log_error(
					f"Missing exchange rate from {price_list_currency} to {company_currency}",
					"POS Awesome",
				)

		item["price_list_currency"] = price_list_currency
		item["plc_conversion_rate"] = exchange_rate
		item["conversion_rate"] = exchange_rate

		if doc:
			doc.price_list_currency = price_list_currency
			doc.plc_conversion_rate = exchange_rate
			doc.conversion_rate = exchange_rate

	# Add company and doctype to the item args for ERPNext validation
	if company:
		item["company"] = company

	# Set doctype for ERPNext validation
	item["doctype"] = "Sales Invoice"

	# Create a proper doc structure with company for ERPNext validation
	if not doc and company:
		doc = frappe._dict({
			"doctype": "Sales Invoice", 
			"company": company,
			"selling_price_list": price_list,
			"price_list_currency": price_list_currency,
			"plc_conversion_rate": exchange_rate,
			"conversion_rate": exchange_rate
		})
	elif doc:
		# Ensure doc has all required currency fields
		doc.selling_price_list = price_list
		doc.price_list_currency = price_list_currency
		doc.plc_conversion_rate = exchange_rate
		doc.conversion_rate = exchange_rate

	max_discount = frappe.get_value("Item", item_code, "max_discount")
	
	# Try to get price directly first, then use get_item_details for other fields
	direct_price = 0.0
	try:
		direct_price_result = frappe.db.sql("""
			SELECT price_list_rate
			FROM `tabItem Price`
			WHERE item_code = %s 
			AND price_list = %s
			AND selling = 1
			AND (valid_from IS NULL OR valid_from <= CURDATE())
			AND (valid_upto IS NULL OR valid_upto >= CURDATE())
			ORDER BY valid_from DESC, modified DESC
			LIMIT 1
		""", (item_code, price_list), as_dict=True)
		
		if direct_price_result and len(direct_price_result) > 0:
			direct_price = flt(direct_price_result[0].price_list_rate or 0.0)
	except Exception as e:
		frappe.logger().error(f"Error getting direct price for {item_code}: {str(e)}")
	
	res = get_item_details(
		item,
		doc,
		overwrite_warehouse=False,
	)
	
	# If ERPNext didn't find a price but we found one directly, use our price
	if (not res.get("price_list_rate") or res.get("price_list_rate") == 0) and direct_price > 0:
		res["price_list_rate"] = direct_price
		res["rate"] = direct_price
		res["base_price_list_rate"] = direct_price
		res["base_rate"] = direct_price
		res["fallback_price_used"] = True
		frappe.logger().info(f"Used direct price {direct_price} for {item_code} instead of ERPNext price {res.get('price_list_rate', 0)}")
	else:
		res["fallback_price_used"] = False
	
	if item.get("is_stock_item") and warehouse:
		res["actual_qty"] = get_stock_availability(item_code, warehouse)
	res["max_discount"] = max_discount
	res["batch_no_data"] = batch_no_data
	res["serial_no_data"] = serial_no_data

	# Add UOMs data directly from item document
	uoms = frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": item_code},
		fields=["uom", "conversion_factor"],
	)

	# Add stock UOM if not already in uoms list
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if stock_uom:
		stock_uom_exists = False
		for uom_data in uoms:
			if uom_data.get("uom") == stock_uom:
				stock_uom_exists = True
				break

		if not stock_uom_exists:
			uoms.append({"uom": stock_uom, "conversion_factor": 1.0})

	res["item_uoms"] = uoms

	return res


@frappe.whitelist()
def get_items_from_barcode(selling_price_list, currency, barcode):
	search_item = frappe.db.get_value(
		"Item Barcode",
		{"barcode": barcode},
		["parent as item_code", "posa_uom"],
		as_dict=1,
	)
	if search_item:
		item_doc = frappe.get_cached_doc("Item", search_item.item_code)
		item_price = frappe.db.get_value(
			"Item Price",
			{
				"item_code": search_item.item_code,
				"price_list": selling_price_list,
				"currency": currency,
			},
			"price_list_rate",
		)

		return {
			"item_code": item_doc.name,
			"item_name": item_doc.item_name,
			"barcode": barcode,
			"rate": item_price or 0,
			"uom": search_item.posa_uom or item_doc.stock_uom,
			"currency": currency,
		}
	return None


def build_item_cache(item_code):
	"""Build item cache for faster access."""
	# Implementation for building item cache
	pass


def get_item_optional_attributes(item_code):
	"""Get optional attributes for an item."""
	return frappe.get_all(
		"Item Variant Attribute",
		fields=["attribute", "attribute_value"],
		filters={"parent": item_code, "parentfield": "attributes"},
	)


@frappe.whitelist()
def get_item_attributes(item_code):
	"""Get item attributes."""
	return frappe.get_all(
		"Item Attribute",
		fields=["name", "attribute_name"],
		filters={
			"name": [
				"in",
				[
					attr.attribute
					for attr in frappe.get_all(
						"Item Variant Attribute",
						fields=["attribute"],
						filters={"parent": item_code},
					)
				],
			]
		},
	)


@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value, search_serial_no):
	"""Search for items by serial number, batch number, or barcode."""
	# Search by barcode
	barcode_data = frappe.db.get_value(
		"Item Barcode",
		{"barcode": search_value},
		["parent as item_code", "barcode"],
		as_dict=True,
	)
	if barcode_data:
		return {"item_code": barcode_data.item_code, "barcode": barcode_data.barcode}

	# Search by batch number
	batch_data = frappe.db.get_value(
		"Batch",
		{"name": search_value},
		["item as item_code", "name as batch_no"],
		as_dict=True,
	)
	if batch_data:
		return {"item_code": batch_data.item_code, "batch_no": batch_data.batch_no}

	# Search by serial number if enabled
	if search_serial_no:
		serial_data = frappe.db.get_value(
			"Serial No",
			{"name": search_value},
			["item_code", "name as serial_no"],
			as_dict=True,
		)
		if serial_data:
			return {
				"item_code": serial_data.item_code,
				"serial_no": serial_data.serial_no,
			}

	return {}


@frappe.whitelist()
def update_price_list_rate(item_code, price_list, rate, uom=None):
	"""Create or update Item Price for the given item and price list."""
	if not item_code or not price_list:
		frappe.throw(_("Item Code and Price List are required"))

	rate = flt(rate)
	filters = {"item_code": item_code, "price_list": price_list}
	if uom:
		filters["uom"] = uom
	else:
		filters["uom"] = ["", None]

	name = frappe.db.exists("Item Price", filters)
	if name:
		doc = frappe.get_doc("Item Price", name)
		doc.price_list_rate = rate
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list,
				"uom": uom,
				"price_list_rate": rate,
				"selling": 1,
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
	return _("Item Price has been added or updated")


@frappe.whitelist()
def get_price_for_uom(item_code, price_list, uom):
	"""Return Item Price for the given item, price list and UOM if it exists."""
	if not (item_code and price_list and uom):
		return None

	price = frappe.db.get_value(
		"Item Price",
		{
			"item_code": item_code,
			"price_list": price_list,
			"uom": uom,
			"selling": 1,
		},
		"price_list_rate",
	)
	return price


@frappe.whitelist()
def check_for_changes(pos_profile, price_list, modified_after):
	"""
	Check for changes in items, prices, stock, UOMs, customers, and other related data since last sync.
	Returns information about what has changed without returning full data.
	"""
	try:
		pos_profile = json.loads(pos_profile) if isinstance(pos_profile, str) else pos_profile
		
		# Parse the modified_after timestamp
		from frappe.utils import get_datetime, add_to_date, now_datetime
		
		# If no last sync time provided, check for changes in the last 24 hours
		if not modified_after:
			modified_since = add_to_date(now_datetime(), hours=-24)
			frappe.logger().info("No previous sync time, checking for changes in last 24 hours")
		else:
			try:
				modified_since = get_datetime(modified_after)
			except Exception as e:
				frappe.logger().warning(f"Invalid modified_after timestamp '{modified_after}': {e}")
				# Fallback to 24 hours ago if timestamp is invalid
				modified_since = add_to_date(now_datetime(), hours=-24)
		
		frappe.logger().info(f"Checking for changes since: {modified_since}")
		frappe.logger().info(f"POS Profile: {pos_profile.get('name')}")
		frappe.logger().info(f"Price List: {price_list}")
		
		# Check for item changes (including name changes, description, etc.)
		changed_items = frappe.db.sql("""
			SELECT name as item_code, modified, item_name, description
			FROM `tabItem`
			WHERE disabled = 0 
			AND is_sales_item = 1
			AND modified > %s
			ORDER BY modified DESC
			LIMIT 100
		""", (modified_since,), as_dict=True)
		
		# Check for price changes
		price_changes = frappe.db.sql("""
			SELECT DISTINCT ip.item_code, ip.modified, ip.price_list_rate
			FROM `tabItem Price` ip
			WHERE ip.price_list = %s
			AND ip.selling = 1
			AND ip.modified > %s
			ORDER BY ip.modified DESC
			LIMIT 100
		""", (price_list, modified_since), as_dict=True)
		
		# Check for UOM Conversion Detail changes
		uom_changes = frappe.db.sql("""
			SELECT DISTINCT parent as item_code, modified
			FROM `tabUOM Conversion Detail`
			WHERE modified > %s
			ORDER BY modified DESC
			LIMIT 100
		""", (modified_since,), as_dict=True)
		
		# Check for Item Barcode changes
		barcode_changes = frappe.db.sql("""
			SELECT DISTINCT parent as item_code, modified
			FROM `tabItem Barcode`
			WHERE modified > %s
			ORDER BY modified DESC
			LIMIT 100
		""", (modified_since,), as_dict=True)
		
		# Check for Customer changes (new customers or modifications)
		customer_changes = frappe.db.sql("""
			SELECT name as customer_code, customer_name, modified
			FROM `tabCustomer`
			WHERE disabled = 0
			AND modified > %s
			ORDER BY modified DESC
			LIMIT 50
		""", (modified_since,), as_dict=True)
		
		# Check for Item Group changes
		item_group_changes = frappe.db.sql("""
			SELECT name as item_group_name, modified
			FROM `tabItem Group`
			WHERE modified > %s
			ORDER BY modified DESC
			LIMIT 50
		""", (modified_since,), as_dict=True)
		
		# Check for Batch changes (new batches or modifications)
		batch_changes = frappe.db.sql("""
			SELECT DISTINCT item as item_code, modified
			FROM `tabBatch`
			WHERE modified > %s
			ORDER BY modified DESC
			LIMIT 100
		""", (modified_since,), as_dict=True)
		
		# Check for Serial Number changes
		serial_changes = frappe.db.sql("""
			SELECT DISTINCT item_code, modified
			FROM `tabSerial No`
			WHERE modified > %s
			ORDER BY modified DESC
			LIMIT 100
		""", (modified_since,), as_dict=True)
		
		# Check for stock changes (if using specific warehouse)
		stock_changes = []
		if pos_profile.get("warehouse"):
			stock_changes = frappe.db.sql("""
				SELECT DISTINCT sle.item_code, sle.modified, sle.actual_qty
				FROM `tabStock Ledger Entry` sle
				WHERE sle.warehouse = %s
				AND sle.is_cancelled = 0
				AND sle.modified > %s
				ORDER BY sle.modified DESC
				LIMIT 100
			""", (pos_profile.get("warehouse"), modified_since), as_dict=True)
		
		# Combine all changed items
		all_changed_items = set()
		change_details = {
			"item_changes": [],
			"price_changes": [],
			"uom_changes": [],
			"barcode_changes": [],
			"customer_changes": [],
			"item_group_changes": [],
			"batch_changes": [],
			"serial_changes": [],
			"stock_changes": []
		}
		
		# Process item changes
		for item in changed_items:
			all_changed_items.add(item["item_code"])
			change_details["item_changes"].append({
				"item_code": item["item_code"],
				"item_name": item["item_name"],
				"description": item["description"],
				"modified": str(item["modified"])
			})
		
		# Process price changes
		for price in price_changes:
			all_changed_items.add(price["item_code"])
			change_details["price_changes"].append({
				"item_code": price["item_code"],
				"price": price["price_list_rate"],
				"modified": str(price["modified"])
			})
		
		# Process UOM changes
		for uom in uom_changes:
			if uom["item_code"]:  # Make sure item_code is not None
				all_changed_items.add(uom["item_code"])
				change_details["uom_changes"].append({
					"item_code": uom["item_code"],
					"modified": str(uom["modified"])
				})
		
		# Process barcode changes
		for barcode in barcode_changes:
			if barcode["item_code"]:
				all_changed_items.add(barcode["item_code"])
				change_details["barcode_changes"].append({
					"item_code": barcode["item_code"],
					"modified": str(barcode["modified"])
				})
		
		# Process customer changes
		for customer in customer_changes:
			change_details["customer_changes"].append({
				"customer_code": customer["customer_code"],
				"customer_name": customer["customer_name"],
				"modified": str(customer["modified"])
			})
		
		# Process item group changes
		for group in item_group_changes:
			change_details["item_group_changes"].append({
				"item_group": group["item_group_name"],
				"modified": str(group["modified"])
			})
		
		# Process batch changes
		for batch in batch_changes:
			if batch["item_code"]:
				all_changed_items.add(batch["item_code"])
				change_details["batch_changes"].append({
					"item_code": batch["item_code"],
					"modified": str(batch["modified"])
				})
		
		# Process serial changes
		for serial in serial_changes:
			if serial["item_code"]:
				all_changed_items.add(serial["item_code"])
				change_details["serial_changes"].append({
					"item_code": serial["item_code"],
					"modified": str(serial["modified"])
				})
		
		# Process stock changes
		for stock in stock_changes:
			all_changed_items.add(stock["item_code"])
			change_details["stock_changes"].append({
				"item_code": stock["item_code"],
				"qty": stock["actual_qty"],
				"modified": str(stock["modified"])
			})
		
		has_changes = (len(all_changed_items) > 0 or 
					  len(customer_changes) > 0 or 
					  len(item_group_changes) > 0)
		
		result = {
			"has_changes": has_changes,
			"changed_items": list(all_changed_items),
			"item_changes_count": len(changed_items),
			"price_changes_count": len(price_changes),
			"uom_changes_count": len(uom_changes),
			"barcode_changes_count": len(barcode_changes),
			"customer_changes_count": len(customer_changes),
			"item_group_changes_count": len(item_group_changes),
			"batch_changes_count": len(batch_changes),
			"serial_changes_count": len(serial_changes),
			"stock_changes_count": len(stock_changes),
			"total_item_changes": len(all_changed_items),
			"change_details": change_details
		}
		
		if has_changes:
			change_summary = []
			if len(changed_items) > 0:
				change_summary.append(f"{len(changed_items)} item updates")
			if len(price_changes) > 0:
				change_summary.append(f"{len(price_changes)} price changes")
			if len(uom_changes) > 0:
				change_summary.append(f"{len(uom_changes)} UOM changes")
			if len(barcode_changes) > 0:
				change_summary.append(f"{len(barcode_changes)} barcode changes")
			if len(customer_changes) > 0:
				change_summary.append(f"{len(customer_changes)} customer changes")
			if len(item_group_changes) > 0:
				change_summary.append(f"{len(item_group_changes)} item group changes")
			if len(batch_changes) > 0:
				change_summary.append(f"{len(batch_changes)} batch changes")
			if len(serial_changes) > 0:
				change_summary.append(f"{len(serial_changes)} serial number changes")
			if len(stock_changes) > 0:
				change_summary.append(f"{len(stock_changes)} stock changes")
			
			frappe.logger().info(f"Found changes since {modified_after}: {', '.join(change_summary)}")
		else:
			frappe.logger().info(f"No changes detected since {modified_since} for price list {price_list}")
			frappe.logger().info(f"Checked: {len(changed_items)} items, {len(price_changes)} prices, {len(customer_changes)} customers")
		
		# Add debug info to result for troubleshooting
		result["debug_info"] = {
			"modified_since": str(modified_since),
			"original_modified_after": modified_after,
			"price_list": price_list,
			"pos_profile_name": pos_profile.get("name"),
			"warehouse": pos_profile.get("warehouse")
		}
		
		return result
		
	except Exception as e:
		frappe.logger().error(f"Error checking for changes: {str(e)}")
		return {"has_changes": False, "error": str(e)}


@frappe.whitelist()
def get_items_by_codes(pos_profile, price_list, item_codes):
	"""
	Get specific items by their item codes for selective updates.
	This is more efficient than loading all items when only a few have changed.
	"""
	try:
		pos_profile = json.loads(pos_profile) if isinstance(pos_profile, str) else pos_profile
		item_codes = json.loads(item_codes) if isinstance(item_codes, str) else item_codes
		
		if not item_codes:
			return []
		
		# Limit to reasonable batch size to prevent server overload
		if len(item_codes) > 100:
			item_codes = item_codes[:100]
			frappe.logger().warning(f"Limiting item codes to 100, received {len(item_codes)}")
		
		# Use the existing get_items logic but filter by specific item codes
		warehouse = pos_profile.get("warehouse")
		price_list_name = price_list
		
		# Build item code condition
		item_codes_str = ", ".join([frappe.db.escape(code) for code in item_codes])
		item_code_condition = f" AND item.name IN ({item_codes_str})"
		
		# Get item groups for the POS profile
		from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups
		item_groups = get_item_groups(pos_profile.get("name"))
		
		# Build item group condition if needed
		item_group_condition = ""
		if item_groups:
			item_groups_str = ", ".join([frappe.db.escape(group) for group in item_groups])
			item_group_condition = f" AND item.item_group IN ({item_groups_str})"
		
		query = f"""
			SELECT 
				item.name AS item_code,
				item.item_name,
				item.description,
				item.stock_uom,
				item.image,
				item.is_stock_item,
				item.has_variants,
				item.variant_of,
				item.item_group,
				item.idx AS idx,
				item.has_batch_no,
				item.has_serial_no,
				item.is_fixed_asset,
				item.weight_per_unit,
				item.weight_uom,
				item.max_discount,
				item.brand,
				COALESCE(ip.price_list_rate, 0) AS rate,
				COALESCE(ip.price_list_rate, 0) AS price_list_rate
			FROM `tabItem` item
			LEFT JOIN `tabItem Price` ip ON (
				ip.item_code = item.name 
				AND ip.price_list = %s 
				AND ip.selling = 1
			)
			WHERE item.disabled = 0 
			AND item.is_sales_item = 1
			{item_group_condition}
			{item_code_condition}
			ORDER BY item.item_name
		"""
		
		items = frappe.db.sql(query, (price_list_name,), as_dict=True)
		
		# Process items similar to get_items
		result = []
		for item in items:
			item.rate = flt(item.rate or 0)
			item.price_list_rate = flt(item.price_list_rate or 0)
			
			# Get actual stock quantity - always fetch for Smart Sync updates
			if item.is_stock_item and warehouse:
				try:
					stock_qty = get_stock_availability(item.item_code, warehouse)
					item.actual_qty = flt(stock_qty)
					frappe.logger().info(f"✅ Stock for {item.item_code}: {stock_qty} (is_stock_item: {item.is_stock_item}, warehouse: {warehouse})")
				except Exception as e:
					frappe.logger().error(f"❌ Error getting stock for {item.item_code}: {str(e)}")
					item.actual_qty = 0.0
			else:
				item.actual_qty = 0.0
				if not item.is_stock_item:
					frappe.logger().info(f"📦 Non-stock item {item.item_code}: actual_qty set to 0")
				else:
					frappe.logger().warning(f"⚠️ No warehouse specified for stock item {item.item_code}")
			
			# Get item barcodes
			item_barcode = get_item_barcodes(item.item_code)
			item['item_barcode'] = item_barcode or []
			
			# Get UOMs
			item_uoms = get_item_uoms(item.item_code)
			item['item_uoms'] = item_uoms or []
			
			# Get serial numbers if applicable
			if item.has_serial_no:
				serial_no_data = get_serial_nos(item.item_code, warehouse)
				item['serial_no_data'] = serial_no_data or []
			else:
				item['serial_no_data'] = []
			
			# Get batch numbers if applicable
			if item.has_batch_no:
				batch_no_data = get_batch_nos(item.item_code, warehouse)
				item['batch_no_data'] = batch_no_data or []
			else:
				item['batch_no_data'] = []
			
			# Set currency
			item['currency'] = pos_profile.get('currency', 'USD')
			
			result.append(item)
		
		frappe.logger().info(f"Retrieved {len(result)} specific items for selective update with quantities")
		
		# Log summary of quantities for debugging
		stock_items = [item for item in result if item.is_stock_item]
		frappe.logger().info(f"Stock items: {len(stock_items)}, Non-stock items: {len(result) - len(stock_items)}")
		for item in stock_items[:5]:  # Log first 5 stock items for debugging
			frappe.logger().info(f"📊 {item.item_code}: qty={item.actual_qty}, rate={item.rate}")
		
		return result
		
	except Exception as e:
		frappe.logger().error(f"Error getting items by codes: {str(e)}")
		frappe.throw(_("Error retrieving specific items: {0}").format(str(e)))


@frappe.whitelist()
def get_recent_customers(modified_after=None, limit=50):
	"""
	Get recently modified customers for Smart Sync.
	"""
	try:
		from frappe.utils import get_datetime
		
		filters = {"disabled": 0}
		if modified_after:
			modified_since = get_datetime(modified_after)
			filters["modified"] = [">", modified_since]
		
		customers = frappe.get_all(
			"Customer",
			filters=filters,
			fields=[
				"name as customer_code",
				"customer_name",
				"customer_group",
				"territory",
				"default_price_list",
				"mobile_no",
				"email_id",
				"modified"
			],
			limit=limit,
			order_by="modified desc"
		)
		
		return customers
		
	except Exception as e:
		frappe.logger().error(f"Error getting recent customers: {str(e)}")
		return []


def get_item_barcodes(item_code):
	"""Get barcodes for an item."""
	return frappe.db.sql("""
		SELECT barcode, posa_uom 
		FROM `tabItem Barcode` 
		WHERE parent = %s
	""", (item_code,), as_dict=True)


def get_item_uoms(item_code):
	"""Get UOMs for an item."""
	return frappe.db.sql("""
		SELECT uom, conversion_factor 
		FROM `tabUOM Conversion Detail` 
		WHERE parent = %s
	""", (item_code,), as_dict=True)


def get_serial_nos(item_code, warehouse):
	"""Get available serial numbers for an item."""
	return frappe.db.sql("""
		SELECT serial_no, item_code, warehouse
		FROM `tabSerial No`
		WHERE item_code = %s 
		AND warehouse = %s
		AND status = 'Active'
		LIMIT 100
	""", (item_code, warehouse), as_dict=True)


def get_batch_nos(item_code, warehouse):
	"""Get available batch numbers for an item."""
	return frappe.db.sql("""
		SELECT sle.batch_no, 
			   SUM(sle.actual_qty) as available_qty,
			   batch.expiry_date
		FROM `tabStock Ledger Entry` sle
		LEFT JOIN `tabBatch` batch ON batch.name = sle.batch_no
		WHERE sle.item_code = %s 
		AND sle.warehouse = %s 
		AND sle.is_cancelled = 0
		GROUP BY sle.batch_no
		HAVING available_qty > 0
		ORDER BY batch.expiry_date ASC
		LIMIT 100
	""", (item_code, warehouse), as_dict=True)


@frappe.whitelist()
def check_all_item_prices(item_code):
	"""Check all price records for an item to debug pricing issues."""
	try:
		# Get all price records for this item
		all_prices = frappe.db.sql("""
			SELECT name, item_code, price_list, price_list_rate, uom, customer, 
				   selling, buying, valid_from, valid_upto, modified, currency
			FROM `tabItem Price` 
			WHERE item_code = %s 
			ORDER BY price_list_rate DESC, modified DESC
		""", (item_code,), as_dict=True)
		
		return {
			"item_code": item_code,
			"total_price_records": len(all_prices),
			"all_prices": all_prices
		}
		
	except Exception as e:
		frappe.logger().error(f"Error checking item prices: {str(e)}")
		return {"error": str(e)}

@frappe.whitelist()
def test_price_retrieval(item_code, price_list):
	"""Test function to debug price retrieval issues."""
	try:
		frappe.logger().info(f"Testing price retrieval for {item_code} in price list {price_list}")
		
		# Check if item exists
		item_exists = frappe.db.exists("Item", item_code)
		if not item_exists:
			return {"error": f"Item {item_code} does not exist"}
			
		# Check if price list exists
		price_list_exists = frappe.db.exists("Price List", price_list)
		if not price_list_exists:
			return {"error": f"Price List {price_list} does not exist"}
		
		# Get item details
		item_details = frappe.db.get_value("Item", item_code, ["item_name", "is_sales_item", "disabled"], as_dict=True)
		
		# Get all Item Price records for this item and price list
		all_prices = frappe.db.sql("""
			SELECT name, item_code, price_list, price_list_rate, uom, selling, buying, valid_from, valid_upto, modified
			FROM `tabItem Price`
			WHERE item_code = %s 
			AND price_list = %s
			ORDER BY modified DESC
		""", (item_code, price_list), as_dict=True)
		
		# Get the active selling price
		active_selling_price = frappe.db.sql("""
			SELECT name, price_list_rate, uom, valid_from, valid_upto
			FROM `tabItem Price`
			WHERE item_code = %s 
			AND price_list = %s
			AND selling = 1
			AND (valid_from IS NULL OR valid_from <= CURDATE())
			AND (valid_upto IS NULL OR valid_upto >= CURDATE())
			ORDER BY valid_from DESC, modified DESC
			LIMIT 1
		""", (item_code, price_list), as_dict=True)
		
		# Get company and currency details
		company_info = frappe.db.sql("""
			SELECT name, default_currency 
			FROM `tabCompany` 
			LIMIT 1
		""", as_dict=True)
		
		price_list_currency = frappe.db.get_value("Price List", price_list, "currency")
		
		# Get company from defaults
		company = (
			frappe.defaults.get_user_default("Company")
			or frappe.defaults.get_global_default("company")
			or (company_info[0]["name"] if company_info else None)
		)
		
		company_currency = None
		if company:
			company_currency = frappe.db.get_value("Company", company, "default_currency")
		
		# Test the get_item_details function
		from erpnext.stock.get_item_details import get_item_details
		
		test_item = {
			"item_code": item_code,
			"doctype": "Sales Invoice",
			"selling_price_list": price_list,
			"company": company,
			"price_list_currency": price_list_currency,
			"plc_conversion_rate": 1.0,
			"conversion_rate": 1.0
		}
		
		test_doc = frappe._dict({
			"doctype": "Sales Invoice", 
			"selling_price_list": price_list,
			"company": company,
			"price_list_currency": price_list_currency,
			"plc_conversion_rate": 1.0,
			"conversion_rate": 1.0
		})
		
		try:
			erpnext_result = get_item_details(test_item, test_doc)
			erpnext_rate = erpnext_result.get("price_list_rate", 0)
		except Exception as e:
			erpnext_rate = f"Error: {str(e)}"
			erpnext_result = {}
		
		return {
			"item_code": item_code,
			"item_name": item_details.item_name,
			"is_sales_item": item_details.is_sales_item,
			"disabled": item_details.disabled,
			"price_list": price_list,
			"price_list_currency": price_list_currency,
			"company": company,
			"company_currency": company_currency,
			"all_companies": company_info,
			"all_item_prices": all_prices,
			"active_selling_price": active_selling_price[0] if active_selling_price else None,
			"erpnext_rate": erpnext_rate,
			"erpnext_full_result": erpnext_result
		}
		
	except Exception as e:
		frappe.logger().error(f"Error in test_price_retrieval: {str(e)}")
		return {"error": str(e)}

@frappe.whitelist()
def test_stock_availability(item_code, warehouse):
	"""Test function to check stock availability for debugging."""
	try:
		frappe.logger().info(f"Testing stock availability for {item_code} in {warehouse}")
		
		# Check if item exists
		item_exists = frappe.db.exists("Item", item_code)
		if not item_exists:
			return {"error": f"Item {item_code} does not exist"}
		
		# Check if warehouse exists  
		warehouse_exists = frappe.db.exists("Warehouse", warehouse)
		if not warehouse_exists:
			return {"error": f"Warehouse {warehouse} does not exist"}
		
		# Get item details
		item_details = frappe.db.get_value("Item", item_code, ["item_name", "is_stock_item"], as_dict=True)
		
		# Get stock availability
		stock_qty = get_stock_availability(item_code, warehouse)
		
		# Get latest stock ledger entries for reference
		latest_entries = frappe.db.sql("""
			SELECT posting_date, posting_time, qty_after_transaction, actual_qty, voucher_type, voucher_no
			FROM `tabStock Ledger Entry` 
			WHERE item_code = %s 
			AND warehouse = %s 
			AND is_cancelled = 0
			ORDER BY posting_date DESC, posting_time DESC, creation DESC
			LIMIT 5
		""", (item_code, warehouse), as_dict=True)
		
		return {
			"item_code": item_code,
			"item_name": item_details.item_name,
			"is_stock_item": item_details.is_stock_item,
			"warehouse": warehouse,
			"current_stock": stock_qty,
			"latest_entries": latest_entries
		}
		
	except Exception as e:
		frappe.logger().error(f"Error in test_stock_availability: {str(e)}")
		return {"error": str(e)}

@frappe.whitelist()
def test_get_item_detail_simple(item_code):
	"""Test get_item_detail with simplified parameters."""
	try:
		item_json = json.dumps({"item_code": item_code})
		result = get_item_detail(
			item=item_json,
			doc=None,
			warehouse="Stores - PT",
			price_list="Standard Selling",
			company="POS TREND COMPANY"
		)
		
		# Return just the key price fields to avoid logging length issues
		return {
			"item_code": item_code, 
			"price_list_rate": result.get("price_list_rate"),
			"base_price_list_rate": result.get("base_price_list_rate"),
			"rate": result.get("rate"),
			"base_rate": result.get("base_rate"),
			"fallback_used": result.get("fallback_price_used", False)
		}
		
	except Exception as e:
		return {"error": str(e)}

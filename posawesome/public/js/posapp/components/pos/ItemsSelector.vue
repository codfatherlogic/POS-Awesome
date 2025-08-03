<template>
	<div :style="responsiveStyles">
		<v-card
			:class="[
				'selection mx-auto my-0 py-0 mt-3 dynamic-card resizable',
				isDarkTheme ? '' : 'bg-grey-lighten-5',
			]"
			:style="{
				height: responsiveStyles['--container-height'],
				maxHeight: responsiveStyles['--container-height'],
				backgroundColor: isDarkTheme ? '#121212' : '',
				resize: 'vertical',
				overflow: 'auto',
			}"
		>
			<v-progress-linear
				:active="loading"
				:indeterminate="loading"
				absolute
				location="top"
				color="info"
			></v-progress-linear>
			<v-overlay :model-value="loading" class="align-center justify-center" absolute>
				<v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
			</v-overlay>
			<!-- Add dynamic-padding wrapper like Invoice component -->
			<div class="dynamic-padding">
				<v-row class="items">
					<v-col class="pb-0">
						<v-text-field
							density="compact"
							clearable
							autofocus
							variant="solo"
							color="primary"
							:label="frappe._('Search Items')"
							hint="Search by item code, serial number, batch no or barcode"
							hide-details
							v-model="debounce_search"
							@keydown.esc="esc_event"
							@keydown.enter="handleEnterKey"
							@click:clear="clearSearch"
							prepend-inner-icon="mdi-magnify"
							@focus="handleItemSearchFocus"
							ref="debounce_search"
						>
							<!-- Add camera scan button if enabled -->
							<template v-slot:append-inner v-if="pos_profile.posa_enable_camera_scanning">
								<v-btn
									icon="mdi-camera"
									size="small"
									color="primary"
									variant="text"
									@click="startCameraScanning"
									:title="__('Scan with Camera')"
								>
								</v-btn>
							</template>
						</v-text-field>
					</v-col>
					<v-col cols="3" class="pb-0" v-if="pos_profile.posa_input_qty">
						<v-text-field
							density="compact"
							variant="solo"
							color="primary"
							:label="frappe._('QTY')"
							hide-details
							v-model="debounce_qty"
							type="text"
							@keydown.enter="enter_event"
							@keydown.esc="esc_event"
							@focus="clearQty"
						></v-text-field>
					</v-col>
					<v-col cols="2" class="pb-0" v-if="pos_profile.posa_new_line">
						<v-checkbox
							v-model="new_line"
							color="accent"
							value="true"
							label="NLine"
							density="default"
							hide-details
						></v-checkbox>
					</v-col>
					<v-col cols="12" class="dynamic-margin-xs">
						<div class="settings-container">
							<v-btn
								density="compact"
								variant="text"
								color="primary"
								prepend-icon="mdi-cog-outline"
								@click="toggleItemSettings"
								class="settings-btn"
							>
								{{ __("Settings") }}
							</v-btn>
							<v-spacer></v-spacer>
							<v-btn
								density="compact"
								variant="text"
								color="primary"
								prepend-icon="mdi-refresh"
								@click="forceReloadItems"
								class="settings-btn"
							>
								{{ __("Reload Items") }}
							</v-btn>

							<v-dialog v-model="show_item_settings" max-width="400px">
								<v-card>
									<v-card-title class="text-h6 pa-4 d-flex align-center">
										<span>{{ __("Item Selector Settings") }}</span>
										<v-spacer></v-spacer>
										<v-btn
											icon="mdi-close"
											variant="text"
											density="compact"
											@click="show_item_settings = false"
										></v-btn>
									</v-card-title>
									<v-divider></v-divider>
									<v-card-text class="pa-4">
										<v-switch
											v-model="temp_hide_qty_decimals"
											:label="__('Hide quantity decimals')"
											hide-details
											density="compact"
											color="primary"
											class="mb-2"
										></v-switch>
										<v-switch
											v-model="temp_hide_zero_rate_items"
											:label="__('Hide zero rated items')"
											hide-details
											density="compact"
											color="primary"
										></v-switch>
										<v-switch
											v-model="temp_enable_custom_items_per_page"
											:label="__('Custom items per page')"
											hide-details
											density="compact"
											color="primary"
											class="mb-2"
										>
										</v-switch>
										<v-text-field
											v-if="temp_enable_custom_items_per_page"
											v-model="temp_items_per_page"
											type="number"
											density="compact"
											variant="outlined"
											color="primary"
											:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
											hide-details
											:label="__('Items per page')"
											class="mb-2 dark-field"
										>
										</v-text-field>
									</v-card-text>
									<v-card-actions class="pa-4 pt-0">
										<v-btn color="error" variant="text" @click="cancelItemSettings">{{
											__("Cancel")
										}}</v-btn>
										<v-spacer></v-spacer>
										<v-btn color="primary" variant="tonal" @click="applyItemSettings">{{
											__("Apply")
										}}</v-btn>
									</v-card-actions>
								</v-card>
							</v-dialog>
						</div>
					</v-col>
					<v-col cols="12" class="pt-0 mt-0">
						<div
							fluid
							class="items-grid dynamic-scroll"
							ref="itemsContainer"
							v-if="items_view == 'card'"
							:style="{ maxHeight: 'calc(100% - 80px)' }"
							@scroll.passive="onCardScroll"
						>
							<v-card
								v-for="item in filtered_items"
								:key="item.item_code"
								hover
								class="dynamic-item-card"
								:draggable="true"
								@dragstart="onDragStart($event, item)"
								@dragend="onDragEnd"
								@click="add_item(item)"
							>
								<v-img
									:src="
										item.image ||
										'/assets/posawesome/js/posapp/components/pos/placeholder-image.png'
									"
									class="text-white align-end"
									gradient="to bottom, rgba(0,0,0,0), rgba(0,0,0,0.4)"
									height="100px"
								>
									<v-card-text class="text-caption px-1 pb-0 truncate">{{
										item.item_name
									}}</v-card-text>
								</v-img>
								<v-card-text class="text--primary pa-1">
									<div class="text-caption text-primary truncate">
										{{
											currencySymbol(item.original_currency || pos_profile.currency) ||
											""
										}}
										{{
											format_currency(
												item.base_price_list_rate || item.rate,
												item.original_currency || pos_profile.currency,
												ratePrecision(item.base_price_list_rate || item.rate),
											)
										}}
									</div>
									<div
										v-if="
											pos_profile.posa_allow_multi_currency &&
											selected_currency !== pos_profile.currency
										"
										class="text-caption text-success truncate"
									>
										{{ currencySymbol(selected_currency) || "" }}
										{{
											format_currency(
												item.rate,
												selected_currency,
												ratePrecision(item.rate),
											)
										}}
									</div>
									<div class="text-caption golden--text truncate">
										{{ format_number(item.actual_qty, hide_qty_decimals ? 0 : 4) || 0 }}
										{{ item.stock_uom || "" }}
									</div>
								</v-card-text>
							</v-card>
						</div>
						<div v-else>
							<v-data-table-virtual
								:headers="headers"
								:items="filtered_items"
								class="sleek-data-table overflow-y-auto"
								:style="{ maxHeight: 'calc(100% - 80px)' }"
								item-key="item_code"
								@click:row="click_item_row"
								@scroll.passive="onListScroll"
							>
								<template v-slot:item.rate="{ item }">
									<div>
										<div class="text-primary">
											{{
												currencySymbol(item.original_currency || pos_profile.currency)
											}}
											{{
												format_currency(
													item.base_price_list_rate || item.rate,
													item.original_currency || pos_profile.currency,
													ratePrecision(item.base_price_list_rate || item.rate),
												)
											}}
										</div>
										<div
											v-if="
												pos_profile.posa_allow_multi_currency &&
												selected_currency !== pos_profile.currency
											"
											class="text-success"
										>
											{{ currencySymbol(selected_currency) }}
											{{
												format_currency(
													item.rate,
													selected_currency,
													ratePrecision(item.rate),
												)
											}}
										</div>
									</div>
								</template>
								<template v-slot:item.actual_qty="{ item }">
									<span class="golden--text">{{
										format_number(item.actual_qty, hide_qty_decimals ? 0 : 4)
									}}</span>
								</template>
							</v-data-table-virtual>
						</div>
					</v-col>
				</v-row>
			</div>
		</v-card>
		<v-card class="cards mb-0 mt-3 dynamic-padding resizable" style="resize: vertical; overflow: auto">
			<v-row no-gutters align="center" justify="center" class="dynamic-spacing-sm">
				<v-col cols="12" class="mb-2">
					<v-select
						:items="items_group"
						:label="frappe._('Items Group')"
						density="compact"
						variant="solo"
						hide-details
						v-model="item_group"
					></v-select>
				</v-col>
				<v-col cols="12" class="mb-2" v-if="pos_profile.posa_enable_price_list_dropdown">
					<v-text-field
						density="compact"
						variant="solo"
						color="primary"
						:label="frappe._('Price List')"
						hide-details
						:model-value="active_price_list"
						readonly
					></v-text-field>
				</v-col>
				<v-col cols="3" class="dynamic-margin-xs">
					<v-btn-toggle v-model="items_view" color="primary" group density="compact" rounded>
						<v-btn size="small" value="list">{{ __("List") }}</v-btn>
						<v-btn size="small" value="card">{{ __("Card") }}</v-btn>
					</v-btn-toggle>
				</v-col>
				<v-col cols="5" class="dynamic-margin-xs">
					<v-btn
						size="small"
						block
						color="warning"
						variant="text"
						@click="show_offers"
						class="action-btn-consistent"
					>
						{{ offersCount }} {{ __("Offers") }}
					</v-btn>
				</v-col>
				<v-col cols="4" class="dynamic-margin-xs">
					<v-btn
						size="small"
						block
						color="primary"
						variant="text"
						@click="show_coupons"
						class="action-btn-consistent"
						>{{ couponsCount }} {{ __("Coupons") }}</v-btn
					>
				</v-col>
			</v-row>
		</v-card>

		<!-- Camera Scanner Component -->
		<CameraScanner
			v-if="pos_profile.posa_enable_camera_scanning"
			ref="cameraScanner"
			:scan-type="pos_profile.posa_camera_scan_type || 'Both'"
			@barcode-scanned="onBarcodeScanned"
		/>
	</div>
</template>

<script type="module">
import format from "../../format";
import _ from "lodash";
import CameraScanner from "./CameraScanner.vue";
import { ensurePosProfile } from "../../../utils/pos_profile.js";
import {
	saveItemUOMs,
	getItemUOMs,
	getLocalStock,
	isOffline,
	initializeStockCache,
	searchStoredItems,
	saveItems,
	clearStoredItems,
	getLocalStockCache,
	setLocalStockCache,
	initPromise,
	memoryInitPromise,
	checkDbHealth,
	getCachedPriceListItems,
	savePriceListItems,
	clearPriceListCache,
	updateLocalStockCache,
	isStockCacheReady,
	getCachedItemDetails,
	saveItemDetailsCache,
	saveItemGroups,
	getCachedItemGroups,
	getItemsLastSync,
	setItemsLastSync,
	forceClearAllCache,
} from "../../../offline/index.js";
import { useResponsive } from "../../composables/useResponsive.js";

export default {
	mixins: [format],
	setup() {
		return useResponsive();
	},
	components: {
		CameraScanner,
	},
	data: () => ({
		pos_profile: {},
		flags: {},
		items_view: "list",
		item_group: "ALL",
		loading: false,
		items_group: ["ALL"],
		items: [],
		search: "",
		first_search: "",
		search_backup: "",
		// Search cache to improve performance for repeated searches
		search_cache: new Map(),
		search_cache_max_size: 100,
		// Limit the displayed items to avoid overly large lists
		itemsPerPage: 50,
		offersCount: 0,
		appliedOffersCount: 0,
		couponsCount: 0,
		appliedCouponsCount: 0,
		customer_price_list: null,
		customer: null,
		new_line: false,
		qty: 1,
		refresh_interval: null,
		currentRequest: null,
		abortController: null,
		itemDetailsRetryCount: 0,
		itemDetailsRetryTimeout: null,
		items_loaded: false,
		selected_currency: "",
		exchange_rate: 1,
		prePopulateInProgress: false,
		itemWorker: null,
		items_request_token: 0,
		show_item_settings: false,
		hide_qty_decimals: false,
		temp_hide_qty_decimals: false,
		hide_zero_rate_items: false,
		temp_hide_zero_rate_items: false,
		isDragging: false,
		// Items per page configuration
		enable_custom_items_per_page: false,
		temp_enable_custom_items_per_page: false,
		items_per_page: 50,
		temp_items_per_page: 50,
		// Page size for incremental item loading. When browser local
		// storage is enabled this will be adjusted to maxLocalStorageItems so items are
		// fetched in manageable batches. Otherwise a high limit
		// effectively disables incremental loading.
		itemsPageLimit: 10000,
		// Maximum items to load in local storage mode to prevent performance issues
		maxLocalStorageItems: 50000, // Increased to handle large datasets
		// Dynamic loading configuration for large datasets
		dynamicLoadingConfig: {
			enabled: true,
			batchSize: 500, // Larger batch size for efficiency
			searchThreshold: 2, // Minimum chars to trigger server search
			maxCachedBatches: 50, // More batches for large datasets
			preloadNext: true, // Preload next batch when near end
		},
		// Cache for dynamic batches
		itemBatches: new Map(),
		totalServerItems: 0,
		// Progressive loading for local storage
		localStorageLoadingConfig: {
			batchSize: 1000, // Load 1000 items per batch
			maxRetries: 3,
			retryDelay: 1000,
		},
		// Track if the current search was triggered by a scanner
		search_from_scanner: false,
		currentPage: 0,
		// Add missing properties to prevent Vue warnings
		initialLoadInProgress: false,
		search_loading: false,
	}),

	watch: {
		customer: _.debounce(function () {
			if (this.pos_profile.posa_force_reload_items) {
				if (this.pos_profile.posa_smart_reload_mode) {
					// When limit search is enabled there may be no items yet.
					// Fallback to full reload if nothing is loaded
					if (!this.items_loaded || !this.filtered_items.length) {
						this.items_loaded = false;
						if (!isOffline()) {
							this.get_items(true);
						} else {
							if (this.pos_profile && !this.pos_profile.posa_local_storage) {
								this.get_items(true);
							} else {
								this.get_items();
							}
						}
					} else {
						// Only refresh prices for visible items when smart reload is enabled
						this.$nextTick(() => this.refreshPricesForVisibleItems());
					}
				} else {
					// Fall back to full reload
					this.items_loaded = false;
					if (!isOffline()) {
						this.get_items(true);
					} else {
						if (this.pos_profile && !this.pos_profile.posa_local_storage) {
							this.get_items(true);
						} else {
							this.get_items();
						}
					}
				}
				return;
			}
			// When the customer changes, avoid reloading all items.
			// Simply refresh prices for visible items only
			if (this.items_loaded && this.filtered_items && this.filtered_items.length > 0) {
				this.$nextTick(() => this.refreshPricesForVisibleItems());
			} else {
				if (this.pos_profile && !this.pos_profile.posa_local_storage) {
					this.get_items(true);
				} else {
					this.get_items();
				}
			}
		}, 300),
		customer_price_list: _.debounce(async function () {
			if (this.pos_profile.posa_force_reload_items) {
				if (this.pos_profile.posa_smart_reload_mode) {
					// When limit search is enabled there may be no items yet.
					// Fallback to full reload if nothing is loaded
					if (!this.items_loaded || !this.items.length) {
						this.items_loaded = false;
						if (!isOffline()) {
							this.get_items(true);
						} else {
							this.get_items();
						}
					} else {
						// Only refresh prices for visible items when smart reload is enabled
						this.$nextTick(() => this.refreshPricesForVisibleItems());
					}
				} else {
					// Fall back to full reload
					this.items_loaded = false;
					if (!isOffline()) {
						this.get_items(true);
					} else {
						this.get_items();
					}
				}
				return;
			}
			// Apply cached rates if available for immediate update
			if (this.items_loaded && this.items && this.items.length > 0) {
				const cached = await getCachedPriceListItems(this.customer_price_list);
				if (cached && cached.length) {
					const map = {};
					cached.forEach((ci) => {
						map[ci.item_code] = ci;
					});
					this.items.forEach((it) => {
						const ci = map[it.item_code];
						if (ci) {
							it.rate = ci.rate;
							it.price_list_rate = ci.price_list_rate || ci.rate;
						}
					});
					this.eventBus.emit("set_all_items", this.items);
					this.update_items_details(this.items);
					return;
				}
			}
			// No cache found - force a reload so prices are updated
			this.items_loaded = false;
			if (!isOffline()) {
				this.get_items(true);
			} else {
				if (this.pos_profile && !this.pos_profile.posa_local_storage) {
					this.get_items(true);
				} else {
					this.get_items();
				}
			}
		}, 300),
		new_line() {
			this.eventBus.emit("set_new_line", this.new_line);
		},
		item_group(newValue, oldValue) {
			if (this.pos_profile && this.pos_profile.pose_use_limit_search && newValue !== oldValue) {
				if (this.pos_profile && !this.pos_profile.posa_local_storage) {
					this.get_items(true);
				} else {
					this.get_items();
				}
			} else if (this.pos_profile && this.pos_profile.posa_local_storage && newValue !== oldValue) {
				this.loadVisibleItems(true);
			}
		},
		filtered_items(new_value, old_value) {
			// Update item details if items changed
			if (
				this.pos_profile &&
				!this.pos_profile.pose_use_limit_search &&
				new_value.length !== old_value.length
			) {
				this.update_items_details(new_value);
			}
		},
		// Automatically search and add item whenever the query changes
		first_search: _.debounce(function (val) {
			console.log("first_search watcher triggered with:", val);
			// If search is cleared and items are not loaded, reload them
			if (!val && (!this.items || this.items.length === 0 || !this.items_loaded)) {
				console.log("first_search watcher: Search cleared and no items, reloading...");
				this.get_items(true);
				return;
			}
			// If search is cleared but items exist, ensure they're visible by triggering reactive update
			if (!val && this.items && this.items.length > 0) {
				console.log("first_search watcher: Search cleared, items exist, triggering update...");
				this.$forceUpdate();
				return;
			}
			// For local storage search, handle search differently
			if (val && this.pos_profile && this.pos_profile.posa_local_storage) {
				console.log("first_search watcher: Local storage search mode");
				// Don't call search_onchange for local storage - let the computed property handle filtering
				return;
			}
			// Call without arguments so search_onchange treats it like an Enter key
			this.search_onchange();
		}, 300),

		// Refresh item prices whenever the user changes currency
		selected_currency() {
			this.applyCurrencyConversionToItems();
		},

		// Also react when exchange rate is adjusted manually
		exchange_rate() {
			this.applyCurrencyConversionToItems();
		},
		windowWidth() {
			// Keep the configured items per page on resize
			this.itemsPerPage = this.items_per_page;
		},
		windowHeight() {
			// Maintain the configured items per page on resize
			this.itemsPerPage = this.items_per_page;
		},
		items_loaded(val) {
			if (val) {
				this.eventBus.emit("items_loaded");
			}
		},
	},

	methods: {
		async loadVisibleItems(reset = false) {
			await initPromise;
			await checkDbHealth();
			
			// Don't clear items if we're just searching - preserve the base items list
			if (reset && !this.first_search) {
				this.currentPage = 0;
				this.items = [];
			}
			
			const search = this.get_search(this.first_search);
			const itemGroup = this.item_group !== "ALL" ? this.item_group.toLowerCase() : "";
			
			console.log("loadVisibleItems called with:", { 
				reset, 
				search: this.first_search, 
				itemGroup, 
				currentItemsCount: this.items?.length || 0 
			});
			
			// Apply local storage limit
			let itemLimit = this.itemsPerPage;
			if (this.pos_profile?.posa_local_storage) {
				const remainingSpace = this.maxLocalStorageItems - (this.items?.length || 0);
				itemLimit = Math.min(itemLimit, remainingSpace);
				
				if (itemLimit <= 0) {
					console.log("Local storage limit reached, not loading more items");
					frappe.show_alert({
						message: __(`Maximum ${this.maxLocalStorageItems} items loaded. Use search to find specific items.`),
						indicator: "blue"
					}, 3);
					return;
				}
			}
			
			const pageItems = await searchStoredItems({
				search,
				itemGroup,
				limit: itemLimit,
				offset: this.currentPage * this.itemsPerPage,
			});
			
			console.log("searchStoredItems returned:", pageItems?.length || 0, "items");
			
			// If no items found in localStorage and we don't have items loaded, fallback to server
			if ((!pageItems || pageItems.length === 0) && (!this.items || this.items.length === 0) && !this.items_loaded) {
				console.log("loadVisibleItems: No items in localStorage, loading from server");
				await this.get_items(false); // Load from server without forcing
				return;
			}
			
			if (reset && !this.first_search) {
				this.items = pageItems;
			} else if (reset && this.first_search) {
				// For search, don't replace items, just let filtering handle it
				console.log("Search mode - not replacing items, keeping:", this.items?.length || 0);
			} else {
				this.items = [...this.items, ...pageItems];
			}
			
			this.eventBus.emit("set_all_items", this.items);
			if (pageItems.length) this.update_items_details(pageItems);
		},
		onCardScroll() {
			const el = this.$refs.itemsContainer;
			if (!el) return;
			if (el.scrollTop + el.clientHeight >= el.scrollHeight - 10) {
				// Use dynamic loading if enabled and not in local storage mode
				if (this.dynamicLoadingConfig.enabled && !this.pos_profile?.posa_local_storage) {
					this.loadMoreItemsOnScroll();
				} else {
					this.currentPage += 1;
					this.loadVisibleItems();
				}
			}
		},
		onListScroll(event) {
			const el = event.target;
			if (el.scrollTop + el.clientHeight >= el.scrollHeight - 10) {
				// Use dynamic loading if enabled and not in local storage mode
				if (this.dynamicLoadingConfig.enabled && !this.pos_profile?.posa_local_storage) {
					this.loadMoreItemsOnScroll();
				} else {
					this.currentPage += 1;
					this.loadVisibleItems();
				}
			}
		},
		refreshPricesForVisibleItems() {
			const vm = this;
			if (!vm.filtered_items || vm.filtered_items.length === 0) return;

			vm.loading = true;

			// Cancel previous request if any
			if (vm.currentRequest) {
				vm.abortController.abort();
				vm.currentRequest = null;
			}

			const itemCodes = vm.filtered_items.map((it) => it.item_code);
			const cacheResult = getCachedItemDetails(vm.pos_profile.name, vm.active_price_list, itemCodes);
			const updates = [];

			cacheResult.cached.forEach((det) => {
				const item = vm.filtered_items.find((it) => it.item_code === det.item_code);
				if (item) {
					const upd = {
						actual_qty: det.actual_qty,
						serial_no_data: det.serial_no_data,
						batch_no_data: det.batch_no_data,
					};
					if (det.item_uoms && det.item_uoms.length > 0) {
						upd.item_uoms = det.item_uoms;
						saveItemUOMs(item.item_code, det.item_uoms);
					}
					if (det.rate !== undefined) {
						if (det.rate !== 0 || !item.rate) {
							upd.rate = det.rate;
							upd.price_list_rate = det.price_list_rate || det.rate;
						}
					}
					updates.push({ item, upd });
				}
			});

			if (cacheResult.missing.length === 0) {
				vm.$nextTick(() => {
					updates.forEach(({ item, upd }) => Object.assign(item, upd));
					updateLocalStockCache(cacheResult.cached);
					vm.loading = false;
				});
				return;
			}

			vm.abortController = new AbortController();
			const itemsToFetch = vm.filtered_items.filter((it) => cacheResult.missing.includes(it.item_code));

			frappe.call({
				method: "posawesome.posawesome.api.items.get_items_details",
				args: {
					pos_profile: JSON.stringify(vm.pos_profile),
					items_data: JSON.stringify(itemsToFetch),
					price_list: vm.active_price_list,
				},
				freeze: false,
				signal: vm.abortController.signal,
				callback: function (r) {
					if (r.message) {
						r.message.forEach((updItem) => {
							const item = vm.filtered_items.find((it) => it.item_code === updItem.item_code);
							if (item) {
								const upd = {
									actual_qty: updItem.actual_qty,
									serial_no_data: updItem.serial_no_data,
									batch_no_data: updItem.batch_no_data,
								};
								if (updItem.item_uoms && updItem.item_uoms.length > 0) {
									upd.item_uoms = updItem.item_uoms;
									saveItemUOMs(item.item_code, updItem.item_uoms);
								}
								if (updItem.rate !== undefined) {
									if (updItem.rate !== 0 || !item.rate) {
										upd.rate = updItem.rate;
										upd.price_list_rate = updItem.price_list_rate || updItem.rate;
									}
								}
								updates.push({ item, upd });
							}
						});

						vm.$nextTick(() => {
							updates.forEach(({ item, upd }) => Object.assign(item, upd));
							updateLocalStockCache(r.message);
							saveItemDetailsCache(vm.pos_profile.name, vm.active_price_list, r.message);
							vm.loading = false;
						});
					}
				},
				error: function (err) {
					if (err.name !== "AbortError") {
						console.error("Error fetching item details:", err);
						vm.loading = false;
					}
				},
			});
		},

		async loadAllItemsForLocalStorage(forceReload = false) {
			const vm = this;
			
			// Wait for POS Profile to be available
			try {
				await this.waitForPosProfile();
			} catch (error) {
				console.error("loadAllItemsForLocalStorage: POS Profile not available:", error);
				frappe.show_alert({
					message: __("POS Profile is not loaded. Please refresh the page."),
					indicator: "red"
				}, 5);
				return false;
			}
			
			// Validate POS Profile first
			if (!vm.pos_profile?.name) {
				console.error("loadAllItemsForLocalStorage: POS Profile not available or invalid");
				frappe.show_alert({
					message: __("POS Profile is not loaded. Please refresh the page."),
					indicator: "red"
				}, 5);
				return false;
			}
			
			if (!vm.pos_profile?.posa_local_storage) {
				console.log("loadAllItemsForLocalStorage: Not in local storage mode");
				return false;
			}
			
			console.log("🏪 Starting progressive loading of ALL items for local storage...");
			
			let allItems = [];
			let offset = 0;
			let hasMoreItems = true;
			let batchCount = 0;
			const batchSize = this.localStorageLoadingConfig.batchSize;
			
			try {
				while (hasMoreItems) {
					batchCount++;
					console.log(`📦 Loading batch ${batchCount} (items ${offset + 1}-${offset + batchSize})`);
					
					const batchItems = await this.loadItemBatchForLocalStorage(offset, batchSize);
					
					if (batchItems && batchItems.length > 0) {
						allItems = [...allItems, ...batchItems];
						offset += batchItems.length;
						
						// Update UI periodically to show progress
						if (batchCount % 2 === 0) {
							vm.items = [...allItems];
							vm.eventBus.emit("set_all_items", vm.items);
							
							frappe.show_alert({
								message: __(`Loading items... ${allItems.length} loaded`),
								indicator: "blue"
							}, 1);
							
							// Allow UI to update
							await new Promise(resolve => setTimeout(resolve, 50));
						}
						
						// Check if we got fewer items than requested (indicates end)
						if (batchItems.length < batchSize) {
							hasMoreItems = false;
						}
						
						// Safety check to prevent infinite loops
						if (offset > 100000) {
							console.warn("Safety limit reached, stopping at 100,000 items");
							hasMoreItems = false;
						}
					} else {
						hasMoreItems = false;
					}
				}
				
				// Final update with all items
				if (allItems.length > 0) {
					// Ensure UOMs for all items
					allItems.forEach((item) => {
						if (!item.item_uoms || item.item_uoms.length === 0) {
							const cached = getItemUOMs(item.item_code);
							if (cached.length > 0) {
								item.item_uoms = cached;
							} else if (item.stock_uom) {
								item.item_uoms = [{ uom: item.stock_uom, conversion_factor: 1.0 }];
							}
						}
					});
					
					vm.items = allItems;
					vm.items_loaded = true;
					vm.eventBus.emit("set_all_items", vm.items);
					
					// Save to local storage cache
					await savePriceListItems(vm.customer_price_list, allItems);
					await saveItems(allItems);
					
					console.log(`✅ Successfully loaded ${allItems.length} items for local storage`);
					
					frappe.show_alert({
						message: __(`Loaded ${allItems.length} items successfully!`),
						indicator: "green"
					}, 3);
					
					// Update item groups
					const groups = Array.from(
						new Set(
							allItems
								.map((it) => it.item_group)
								.filter((g) => g && g !== "All Item Groups"),
						),
					);
					saveItemGroups(groups);
					
					// Update item details for first batch to get quantities
					if (allItems.length > 0) {
						const firstBatch = allItems.slice(0, 200);
						vm.update_items_details(firstBatch);
					}
					
					return true;
				} else {
					console.warn("No items loaded from server");
					return false;
				}
				
			} catch (error) {
				console.error("Error loading all items for local storage:", error);
				frappe.show_alert({
					message: __("Error loading items. Please try again."),
					indicator: "red"
				}, 5);
				return false;
			}
		},

		async loadItemBatchForLocalStorage(offset, limit) {
			const vm = this;
			
			// Validate POS Profile
			if (!vm.pos_profile?.name) {
				console.error("loadItemBatchForLocalStorage: POS Profile not available");
				throw new Error("POS Profile not available");
			}
			
			try {
				const response = await new Promise((resolve, reject) => {
					frappe.call({
						method: "posawesome.posawesome.api.items.get_items",
						args: {
							pos_profile: JSON.stringify(vm.pos_profile),
							price_list: vm.customer_price_list,
							item_group: vm.item_group !== "ALL" ? vm.item_group.toLowerCase() : "",
							search_value: "", // No search for full load
							customer: vm.customer,
							limit: limit,
							offset: offset,
						},
						freeze: false,
						timeout: 60000, // 60 second timeout for large batches
						callback: resolve,
						error: reject
					});
				});
				
				if (response.message && Array.isArray(response.message)) {
					console.log(`Loaded batch: ${response.message.length} items (offset: ${offset})`);
					return response.message;
				} else {
					console.warn("Invalid response format:", response);
					return [];
				}
				
			} catch (error) {
				console.error(`Error loading batch at offset ${offset}:`, error);
				
				// Retry logic
				for (let retry = 1; retry <= this.localStorageLoadingConfig.maxRetries; retry++) {
					console.log(`Retrying batch load (attempt ${retry}/${this.localStorageLoadingConfig.maxRetries})`);
					
					await new Promise(resolve => setTimeout(resolve, this.localStorageLoadingConfig.retryDelay));
					
					try {
						const retryResponse = await new Promise((resolve, reject) => {
							frappe.call({
								method: "posawesome.posawesome.api.items.get_items",
								args: {
									pos_profile: JSON.stringify(vm.pos_profile),
									price_list: vm.customer_price_list,
									item_group: vm.item_group !== "ALL" ? vm.item_group.toLowerCase() : "",
									search_value: "",
									customer: vm.customer,
									limit: limit,
									offset: offset,
								},
								freeze: false,
								timeout: 60000,
								callback: resolve,
								error: reject
							});
						});
						
						if (retryResponse.message && Array.isArray(retryResponse.message)) {
							console.log(`Retry successful: ${retryResponse.message.length} items`);
							return retryResponse.message;
						}
					} catch (retryError) {
						console.error(`Retry ${retry} failed:`, retryError);
						if (retry === this.localStorageLoadingConfig.maxRetries) {
							console.error("All retries failed, returning empty array");
							return [];
						}
					}
				}
				
				return [];
			}
		},

		async loadItemBatch(batchIndex, searchTerm = "") {
			const batchKey = `${batchIndex}_${searchTerm}`;
			
			// Return cached batch if available
			if (this.itemBatches.has(batchKey)) {
				console.log(`Returning cached batch ${batchIndex} for search: "${searchTerm}"`);
				return this.itemBatches.get(batchKey);
			}
			
			const vm = this;
			
			// Validate POS Profile
			if (!vm.pos_profile?.name) {
				console.error("loadItemBatch: POS Profile not available");
				return { items: [], batchIndex, searchTerm, totalCount: 0, timestamp: Date.now() };
			}
			
			const offset = batchIndex * this.dynamicLoadingConfig.batchSize;
			
			try {
				console.log(`Loading batch ${batchIndex} (offset: ${offset}) for search: "${searchTerm}"`);
				
				const response = await new Promise((resolve, reject) => {
					frappe.call({
						method: "posawesome.posawesome.api.items.get_items",
						args: {
							pos_profile: JSON.stringify(vm.pos_profile),
							price_list: vm.customer_price_list,
							item_group: vm.item_group !== "ALL" ? vm.item_group.toLowerCase() : "",
							search_value: searchTerm,
							customer: vm.customer,
							limit: this.dynamicLoadingConfig.batchSize,
							offset: offset,
						},
						freeze: false,
						callback: resolve,
						error: reject
					});
				});
				
				if (response.message) {
					const batchData = {
						items: response.message,
						batchIndex,
						searchTerm,
						totalCount: response.total_count || response.message.length,
						timestamp: Date.now()
					};
					
					// Cache the batch
					this.itemBatches.set(batchKey, batchData);
					this.totalServerItems = batchData.totalCount;
					
					// Clean old batches if we exceed the limit
					if (this.itemBatches.size > this.dynamicLoadingConfig.maxCachedBatches) {
						const oldestKey = Array.from(this.itemBatches.keys())[0];
						this.itemBatches.delete(oldestKey);
					}
					
					console.log(`Loaded batch ${batchIndex}: ${batchData.items.length} items`);
					return batchData;
				}
			} catch (error) {
				console.error(`Error loading batch ${batchIndex}:`, error);
				return { items: [], batchIndex, searchTerm, totalCount: 0, timestamp: Date.now() };
			}
		},

		async loadItemsWithDynamicStrategy(searchTerm = "", forceReload = false) {
			const vm = this;
			
			// For short search terms, use local filtering if we have items
			if (searchTerm.length > 0 && searchTerm.length < this.dynamicLoadingConfig.searchThreshold && this.items.length > 0) {
				console.log("Using local filtering for short search term:", searchTerm);
				return;
			}
			
			// Clear existing batches on new search or force reload
			if (forceReload) {
				this.itemBatches.clear();
				this.items = [];
			}
			
			// Load first batch
			const firstBatch = await this.loadItemBatch(0, searchTerm);
			if (firstBatch && firstBatch.items.length > 0) {
				// Ensure UOMs for items
				firstBatch.items.forEach((item) => {
					if (!item.item_uoms || item.item_uoms.length === 0) {
						const cached = getItemUOMs(item.item_code);
						if (cached.length > 0) {
							item.item_uoms = cached;
						} else if (item.stock_uom) {
							item.item_uoms = [{ uom: item.stock_uom, conversion_factor: 1.0 }];
						}
					}
				});
				
				vm.items = firstBatch.items;
				vm.items_loaded = true;
				vm.eventBus.emit("set_all_items", vm.items);
				
				// Preload next batch if enabled and there are more items
				if (this.dynamicLoadingConfig.preloadNext && firstBatch.items.length === this.dynamicLoadingConfig.batchSize) {
					setTimeout(() => {
						this.loadItemBatch(1, searchTerm);
					}, 100);
				}
				
				console.log(`Dynamic loading: Loaded ${vm.items.length} items, total available: ${this.totalServerItems}`);
			}
		},

		async loadMoreItemsOnScroll() {
			// Calculate which batch we need based on current items
			const currentBatchCount = Math.ceil(this.items.length / this.dynamicLoadingConfig.batchSize);
			const searchTerm = this.get_search(this.first_search) || "";
			
			// Check if we've already loaded all available items
			if (this.items.length >= this.totalServerItems) {
				console.log("All available items loaded");
				return;
			}
			
			const nextBatch = await this.loadItemBatch(currentBatchCount, searchTerm);
			if (nextBatch && nextBatch.items.length > 0) {
				// Ensure UOMs for new items
				nextBatch.items.forEach((item) => {
					if (!item.item_uoms || item.item_uoms.length === 0) {
						const cached = getItemUOMs(item.item_code);
						if (cached.length > 0) {
							item.item_uoms = cached;
						} else if (item.stock_uom) {
							item.item_uoms = [{ uom: item.stock_uom, conversion_factor: 1.0 }];
						}
					}
				});
				
				this.items = [...this.items, ...nextBatch.items];
				this.eventBus.emit("set_all_items", this.items);
				
				console.log(`Scroll loading: Now have ${this.items.length} items, total available: ${this.totalServerItems}`);
			}
		},

		show_offers() {
			this.eventBus.emit("show_offers", "true");
		},
		show_coupons() {
			this.eventBus.emit("show_coupons", "true");
		},
		async forceReloadItems() {
			console.log("Force reloading items via button...");
			
			// Show loading message
			frappe.show_alert({
				message: __("Reloading all items..."),
				indicator: "blue"
			}, 3);
			
			// Clear all caches
			this.search_cache.clear();
			this.items = [];
			this.items_loaded = false;
			
			// Clear cached price list items so the reload always
			// fetches the latest data from the server
			await clearPriceListCache();
			
			// Clear local storage cache if enabled
			if (this.pos_profile && this.pos_profile.posa_local_storage) {
				try {
					const cacheKeys = [
						`items_${this.customer_price_list}`,
						`items_cache_${this.customer_price_list}`,
						'posawesome_items_last_sync'
					];
					cacheKeys.forEach(key => {
						localStorage.removeItem(key);
					});
					
					console.log("🏪 Cleared local storage cache, will load ALL items");
				} catch (e) {
					console.error("Failed to clear localStorage cache:", e);
				}
			}
			
			// Clear dynamic loading cache
			this.itemBatches.clear();
			
			// Always recreate the worker when forcing a reload so
			// subsequent reloads fetch fresh data from the server.
			if (!this.itemWorker && typeof Worker !== "undefined") {
				try {
					const workerUrl = "/assets/posawesome/js/posapp/workers/itemWorker.js";
					this.itemWorker = new Worker(workerUrl, { type: "classic" });
				} catch (e) {
					console.error("Failed to start item worker", e);
					this.itemWorker = null;
				}
			}
			
			// For local storage mode, use progressive loading to get ALL items
			if (this.pos_profile && this.pos_profile.posa_local_storage) {
				console.log("🏪 Force reload in local storage mode - loading ALL items");
				const success = await this.loadAllItemsForLocalStorage(true);
				if (success) {
					this.loading = false;
					return;
				}
			}
			
			// Fallback to regular loading
			this.get_items(true);
		},
		async get_items(force_server = false) {
			await initPromise;
			await checkDbHealth();
			const request_token = ++this.items_request_token;
			
			// Wait for POS Profile to be available
			try {
				await this.waitForPosProfile();
			} catch (error) {
				console.error("get_items: POS Profile not available:", error);
				this.loading = false;
				frappe.show_alert({
					message: __("POS Profile is not loaded. Please refresh the page."),
					indicator: "red"
				}, 5);
				return;
			}
			
			// Enhanced POS Profile validation
			if (!this.pos_profile) {
				console.error("No POS Profile available");
				this.loading = false;
				frappe.show_alert({
					message: __("POS Profile is not loaded. Please refresh the page."),
					indicator: "red"
				}, 5);
				return;
			}
			
			// Validate essential POS Profile properties
			if (!this.pos_profile.name) {
				console.error("POS Profile has no name property:", this.pos_profile);
				this.loading = false;
				frappe.show_alert({
					message: __("Invalid POS Profile. Please contact administrator."),
					indicator: "red"
				}, 5);
				return;
			}
			
			console.log("Using POS Profile:", this.pos_profile.name);

			const shouldClear = force_server && this.pos_profile.posa_local_storage && !isOffline();
			let cleared = false;

			const vm = this;
			this.loading = true;
			const syncSince = getItemsLastSync();

			// Debug log for troubleshooting
			console.log("get_items called:", { 
				force_server, 
				items_loaded: this.items_loaded, 
				current_items_count: this.items?.length || 0,
				search: this.first_search,
				pose_use_limit_search: this.pos_profile?.pose_use_limit_search,
				posa_local_storage: this.pos_profile?.posa_local_storage
			});
			
			let search = this.get_search(this.first_search);
			let gr = vm.item_group !== "ALL" ? vm.item_group.toLowerCase() : "";
			let sr = search || "";

			// For non-local storage mode with large datasets, use dynamic loading strategy
			const isNonLocalStorageMode = !this.pos_profile?.posa_local_storage;
			const shouldUseDynamicLoading = isNonLocalStorageMode && this.dynamicLoadingConfig.enabled && !this.pos_profile?.pose_use_limit_search;

			if (shouldUseDynamicLoading) {
				console.log("Using dynamic loading strategy for large dataset");
				await this.loadItemsWithDynamicStrategy(sr, force_server);
				this.loading = false;
				return;
			}

			// For non-local storage mode, use pagination/lazy loading
			const shouldUsePagination = isNonLocalStorageMode && !this.pos_profile?.pose_use_limit_search;

			// Modified skip reload logic - be more aggressive about reloading when no items are present
			if (
				this.items_loaded &&
				!force_server &&
				!this.first_search &&
				this.pos_profile &&
				!this.pos_profile.pose_use_limit_search &&
				this.items && 
				this.items.length > 0  // Only skip if we actually have items
			) {
				console.info("Items already loaded, skipping reload");
				if (this.filtered_items && this.filtered_items.length > 0) {
					this.update_items_details(this.filtered_items);
				}
				this.loading = false;
				return;
			}
			// Removed noisy debug log

			// Attempt to load cached items for the current price list
			if (
				!force_server &&
				this.pos_profile &&
				this.pos_profile.posa_local_storage &&
				!this.pos_profile.pose_use_limit_search
			) {
				const cached = await getCachedPriceListItems(vm.customer_price_list);
				if (cached && cached.length) {
					vm.items = cached;
					vm.items.forEach((it) => {
						if (!it.item_uoms || it.item_uoms.length === 0) {
							const cachedUoms = getItemUOMs(it.item_code);
							if (cachedUoms.length > 0) {
								it.item_uoms = cachedUoms;
							} else if (it.stock_uom) {
								it.item_uoms = [{ uom: it.stock_uom, conversion_factor: 1.0 }];
							}
						}
					});
					this.eventBus.emit("set_all_items", vm.items);
					vm.loading = false;
					vm.items_loaded = true;

					if (vm.items && vm.items.length > 0) {
						if (vm.items.length <= 500) {
							vm.prePopulateStockCache(vm.items);
						}
						vm.update_items_details(vm.items);
					}
					return;
				}
			}

			// Load from localStorage when available and not forcing
			if (
				vm.pos_profile &&
				vm.pos_profile.posa_local_storage &&
				!vm.pos_profile.pose_use_limit_search &&
				!force_server
			) {
				console.log("🏪 Local storage mode - attempting to load items...");
				
				// First try to load from cache
				const cached = await getCachedPriceListItems(vm.customer_price_list);
				if (cached && cached.length > 0) {
					console.log(`Found ${cached.length} cached items, loading them first`);
					
					vm.items = cached;
					vm.items.forEach((it) => {
						if (!it.item_uoms || it.item_uoms.length === 0) {
							const cachedUoms = getItemUOMs(it.item_code);
							if (cachedUoms.length > 0) {
								it.item_uoms = cachedUoms;
							} else if (it.stock_uom) {
								it.item_uoms = [{ uom: it.stock_uom, conversion_factor: 1.0 }];
							}
						}
					});
					
					this.eventBus.emit("set_all_items", vm.items);
					vm.loading = false;
					vm.items_loaded = true;

					if (vm.items && vm.items.length > 0) {
						vm.update_items_details(vm.items.slice(0, 200)); // Update first 200 for performance
					}
					
					console.log(`✅ Loaded ${vm.items.length} items from cache`);
					return;
				}
				
				// No cache found, load all items progressively
				console.log("No cached items found, loading ALL items from server...");
				
				frappe.show_alert({
					message: __("Loading all items for local storage... This may take a moment."),
					indicator: "blue"
				}, 3);
				
				const success = await this.loadAllItemsForLocalStorage(force_server);
				
				if (success) {
					vm.loading = false;
					vm.items_loaded = true;
					console.log(`✅ Successfully loaded ${vm.items.length} items`);
					return;
				} else {
					console.log("Failed to load all items, falling back to regular loading");
					// Fall through to regular loading logic
				}
			}
			// Removed noisy debug log

			if (this.itemWorker) {
				try {
					// For local storage mode, don't limit items - load as many as possible
					const requestLimit = vm.pos_profile?.posa_local_storage ? 
						this.maxLocalStorageItems : // Use the large limit for local storage
						this.itemsPageLimit;
						
					console.log("ItemWorker: Loading with limit:", requestLimit, "Local storage mode:", vm.pos_profile?.posa_local_storage);
					
					const res = await fetch("/api/method/posawesome.posawesome.api.items.get_items", {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							"X-Frappe-CSRF-Token": frappe.csrf_token,
						},
						credentials: "same-origin",
						body: JSON.stringify({
							pos_profile: JSON.stringify(vm.pos_profile),
							price_list: vm.customer_price_list,
							item_group: gr,
							search_value: sr,
							customer: vm.customer,
							modified_after: syncSince,
							limit: requestLimit,
							offset: 0,
						}),
					});

					const text = await res.text();
					// console.log(text)
					this.itemWorker.onmessage = async (ev) => {
						if (this.items_request_token !== request_token) return;
						if (ev.data.type === "parsed") {
							const parsed = ev.data.items;
							let newItems = parsed.message || parsed;
							
							// For local storage mode, don't limit the items - take all that are returned
							if (vm.pos_profile?.posa_local_storage) {
								console.log(`ItemWorker: Local storage mode - processing ${newItems.length} items`);
								if (newItems.length > 0) {
									frappe.show_alert({
										message: __(`Loading ${newItems.length} items into local storage...`),
										indicator: "blue"
									}, 2);
								}
							} else if (newItems.length > this.maxLocalStorageItems) {
								// Only limit for non-local storage mode
								console.log(`ItemWorker: Non-local storage mode - limiting items from ${newItems.length} to ${this.maxLocalStorageItems}`);
								newItems = newItems.slice(0, this.maxLocalStorageItems);
								
								vm.$toast.warning(
									`Showing first ${this.maxLocalStorageItems} items. Enable local storage for full item list.`
								);
							}
							
							if (syncSince && vm.items && vm.items.length) {
								const map = new Map(vm.items.map((it) => [it.item_code, it]));
								newItems.forEach((it) => map.set(it.item_code, it));
								vm.items = Array.from(map.values());
							} else {
								vm.items = newItems;
							}
							// Ensure UOMs are available for each item
							vm.items.forEach((it) => {
								if (it.item_uoms && it.item_uoms.length > 0) {
									saveItemUOMs(it.item_code, it.item_uoms);
								} else {
									const cached = getItemUOMs(it.item_code);
									if (cached.length > 0) {
										it.item_uoms = cached;
									} else if (it.stock_uom) {
										it.item_uoms = [{ uom: it.stock_uom, conversion_factor: 1.0 }];
									}
								}
							});
							vm.eventBus.emit("set_all_items", vm.items);
							
							// Check if we need to load more items
							// For local storage mode, continue loading until we get all items
							const shouldContinue = vm.pos_profile?.posa_local_storage ? 
								(newItems.length === this.itemsPageLimit) : // Continue if we got a full batch
								(newItems.length === this.itemsPageLimit);
								
							if (shouldContinue) {
								console.log(`ItemWorker: Loading more items - current total: ${vm.items.length}`);
								this.backgroundLoadItems(this.itemsPageLimit, syncSince, shouldClear);
							} else {
								setItemsLastSync(new Date().toISOString());
								if (vm.itemWorker) {
									vm.itemWorker.terminate();
									vm.itemWorker = null;
								}
								
								// Log final counts
								console.log(`ItemWorker: Final item count: ${vm.items.length}`);
								if (vm.pos_profile?.posa_local_storage) {
									console.log(`✅ Local storage mode - loaded ${vm.items.length} items`);
									frappe.show_alert({
										message: __(`Successfully loaded ${vm.items.length} items!`),
										indicator: "green"
									}, 3);
								}
							}
							vm.loading = false;
							vm.items_loaded = true;
							console.info("Items Loaded");

							const groups = Array.from(
								new Set(
									vm.items
										.map((it) => it.item_group)
										.filter((g) => g && g !== "All Item Groups"),
								),
							);
							saveItemGroups(groups);

							// Pre-populate stock cache when items are freshly loaded
							if (vm.items.length <= 500) {
								vm.prePopulateStockCache(vm.items);
							}

							vm.$nextTick(() => {
								if (vm.search && vm.pos_profile && !vm.pos_profile.pose_use_limit_search) {
									vm.search_onchange();
								}
							});

							// Always refresh quantities after items are loaded
							if (vm.items && vm.items.length > 0) {
								vm.update_items_details(vm.items);
							}
							if (vm.pos_profile && vm.pos_profile.pose_use_limit_search) {
								vm.enter_event();
							}
						} else if (ev.data.type === "error") {
							console.error("Item worker parse error:", ev.data.error);
							vm.loading = false;
						}
					};
					this.itemWorker.postMessage({
						type: "parse_and_cache",
						json: text,
						priceList: vm.customer_price_list || "",
					});
				} catch (err) {
					console.error("Failed to fetch items", err);
					
					// Show user-friendly error message
					frappe.show_alert({
						message: __("Failed to load items. Please check your connection and try again."),
						indicator: "red"
					}, 5);
					
					// Try to load from cache as fallback
					if (this.pos_profile && this.pos_profile.posa_local_storage) {
						console.log("Attempting to load from cache as fallback...");
						try {
							const cachedItems = await getCachedPriceListItems(vm.customer_price_list);
							if (cachedItems && cachedItems.length > 0) {
								vm.items = cachedItems;
								vm.items_loaded = true;
								console.info("Loaded items from cache as fallback");
								
								// Ensure UOMs for cached items
								vm.items.forEach((it) => {
									if (!it.item_uoms || it.item_uoms.length === 0) {
										const cached = getItemUOMs(it.item_code);
										if (cached.length > 0) {
											it.item_uoms = cached;
										} else if (it.stock_uom) {
											it.item_uoms = [{ uom: it.stock_uom, conversion_factor: 1.0 }];
										}
									}
								});
								
								vm.eventBus.emit("set_all_items", vm.items);
								if (vm.items.length > 0) {
									vm.update_items_details(vm.items);
								}
							} else {
								console.warn("No cached items available");
							}
						} catch (cacheError) {
							console.error("Failed to load from cache:", cacheError);
						}
					}
					
					vm.loading = false;
				}
			} else {
				// For non-local storage mode, use smaller page size to prevent hanging
				const effectivePageLimit = shouldUsePagination ? Math.min(vm.itemsPageLimit || 500, 500) : vm.itemsPageLimit;
				
				// For local storage mode, apply the maximum limit
				const finalPageLimit = vm.pos_profile?.posa_local_storage ? 
					Math.min(effectivePageLimit, vm.maxLocalStorageItems) : 
					effectivePageLimit;
				
				console.log("Loading items from server with limit:", finalPageLimit, "Local storage mode:", vm.pos_profile?.posa_local_storage, "Non-local storage mode:", isNonLocalStorageMode);
				
				// Add timeout and improved error handling for slow connections
				const timeoutPromise = new Promise((_, reject) => {
					setTimeout(() => reject(new Error('Request timeout')), 30000); // 30 second timeout
				});
				
				const apiCallPromise = new Promise((resolve, reject) => {
					frappe.call({
						method: "posawesome.posawesome.api.items.get_items",
						args: {
							pos_profile: JSON.stringify(vm.pos_profile),
							price_list: vm.customer_price_list,
							item_group: gr,
							search_value: sr,
							customer: vm.customer,
							modified_after: syncSince,
							limit: finalPageLimit,
							offset: 0,
						},
						freeze: false, // Don't freeze UI for better UX
						timeout: 30000, // 30 second timeout
						callback: function (r) {
							console.log("Raw frappe.call response:", r);
							console.log("Response message:", r?.message);
							console.log("Response exc:", r?.exc);
							console.log("Response exc_type:", r?.exc_type);
							resolve(r);
						},
						error: function (err) {
							console.error("frappe.call error:", err);
							reject(err);
						}
					});
				});
				
				try {
					const r = await Promise.race([apiCallPromise, timeoutPromise]);
					
					if (vm.items_request_token !== request_token) return;
					
					// Enhanced debugging for API response
					console.log("API Response:", r);
					console.log("API Response message:", r.message);
					console.log("API Response message type:", typeof r.message);
					console.log("API Response message length:", r.message?.length);
					
					if (r.message) {
						const newItems = r.message;
						
						// More detailed logging
						console.log("New items received:", newItems);
						console.log("New items count:", newItems.length);
						if (newItems.length > 0) {
							console.log("First new item:", newItems[0]);
						} else {
							console.warn("API returned empty items array!");
						}
						
						if (syncSince && vm.items && vm.items.length) {
							const map = new Map(vm.items.map((it) => [it.item_code, it]));
							newItems.forEach((it) => map.set(it.item_code, it));
							vm.items = Array.from(map.values());
						} else {
							vm.items = newItems;
						}
						
						// Debug the assignment
						console.log("After assignment - vm.items count:", vm.items?.length || 0);
						if (vm.items && vm.items.length > 0) {
							console.log("First assigned item:", vm.items[0]);
						} else {
							console.error("vm.items is still empty after assignment!");
						}
						// Ensure UOMs are available for each item
						vm.items.forEach((it) => {
							if (it.item_uoms && it.item_uoms.length > 0) {
								saveItemUOMs(it.item_code, it.item_uoms);
							} else {
								const cached = getItemUOMs(it.item_code);
								if (cached.length > 0) {
									it.item_uoms = cached;
								} else if (it.stock_uom) {
									it.item_uoms = [{ uom: it.stock_uom, conversion_factor: 1.0 }];
								}
							}
						});
						vm.eventBus.emit("set_all_items", vm.items);
						
						// For non-local storage mode, check if we need to load more items in background
						if (shouldUsePagination && newItems.length === finalPageLimit) {
							console.log("Background loading more items for non-local storage mode");
							this.backgroundLoadItems(finalPageLimit, syncSince, shouldClear);
						} else if (newItems.length === vm.itemsPageLimit && !shouldUsePagination && !vm.pos_profile?.posa_local_storage) {
							this.backgroundLoadItems(vm.itemsPageLimit, syncSince, shouldClear);
						} else if (vm.pos_profile?.posa_local_storage && newItems.length >= vm.maxLocalStorageItems) {
							// For local storage mode, stop loading when we hit the limit
							console.log(`Local storage limit of ${vm.maxLocalStorageItems} items reached, stopping background load`);
							frappe.show_alert({
								message: __(`Loaded maximum ${vm.maxLocalStorageItems} items for performance. Use search to find specific items.`),
								indicator: "blue"
							}, 5);
							setItemsLastSync(new Date().toISOString());
						} else {
							setItemsLastSync(new Date().toISOString());
						}
						
						vm.loading = false;
						vm.items_loaded = true;
						
						// Only save to cache if using local storage
						if (vm.pos_profile && vm.pos_profile.posa_local_storage) {
							await savePriceListItems(vm.customer_price_list, vm.items);
						}
						
						console.info("Items Loaded - Count:", vm.items.length);

						const groups = Array.from(
							new Set(
								vm.items
									.map((it) => it.item_group)
									.filter((g) => g && g !== "All Item Groups"),
							),
						);
						saveItemGroups(groups);

						// Pre-populate stock cache when items are freshly loaded
						// For non-local storage mode, be more conservative about cache size
						const cacheThreshold = shouldUsePagination ? 200 : 500;
						if (vm.items.length <= cacheThreshold) {
							vm.prePopulateStockCache(vm.items);
						}

						vm.$nextTick(() => {
							if (vm.search && vm.pos_profile && !vm.pos_profile.pose_use_limit_search) {
								vm.search_onchange();
							}
						});

						// Always refresh quantities after items are loaded
						if (vm.items && vm.items.length > 0) {
							vm.update_items_details(vm.items);
						}

						if (
							vm.pos_profile &&
							vm.pos_profile.posa_local_storage &&
							!vm.pos_profile.pose_use_limit_search
						) {
							try {
								if (shouldClear && !cleared) {
									await clearStoredItems();
									cleared = true;
								}
								await saveItems(vm.items);
								vm.items.forEach((it) => {
									if (it.item_uoms && it.item_uoms.length > 0) {
										saveItemUOMs(it.item_code, it.item_uoms);
									}
								});
							} catch (e) {
								console.error(e);
							}
						}
						if (vm.pos_profile && vm.pos_profile.pose_use_limit_search) {
							vm.enter_event();
						}
					} else {
						// No message in response - this might be the issue
						console.error("API response has no message property:", r);
						console.error("This could indicate an authentication or permission issue");
						vm.loading = false;
						vm.items_loaded = false;
						
						// Try to show helpful error message
						frappe.show_alert({
							message: __("No items returned from server. Please check permissions or data availability."),
							indicator: "red"
						}, 5);
					}
				} catch (error) {
					vm.loading = false;
					console.error("Error loading items:", error);
					
					// Show user-friendly error message
					if (error.message === 'Request timeout') {
						vm.eventBus.emit("show_message", {
							title: "Search timeout - please try a more specific search term",
							color: "warning",
						});
					} else {
						vm.eventBus.emit("show_message", {
							title: "Error loading items. Please check your connection and try again.",
							color: "error",
						});
					}
					
					// Try to load from cache as fallback
					if (vm.pos_profile && vm.pos_profile.posa_local_storage) {
						try {
							const cached = await getCachedPriceListItems(vm.customer_price_list);
							if (cached && cached.length) {
								vm.items = cached;
								vm.eventBus.emit("set_all_items", vm.items);
								vm.items_loaded = true;
								console.info("Loaded items from cache as fallback");
							}
						} catch (cacheError) {
							console.error("Failed to load from cache:", cacheError);
						}
					}
				}
			}
		},
		async backgroundLoadItems(offset, syncSince, clearBefore = false) {
			const limit = this.itemsPageLimit;
			const isNonLocalStorageMode = !this.pos_profile?.posa_local_storage;
			const isLocalStorageMode = this.pos_profile?.posa_local_storage;
			
			// For local storage mode, don't limit the loading - keep going until all items are loaded
			if (isLocalStorageMode) {
				console.log(`Background loading for local storage: current items ${this.items?.length || 0}`);
				// No limit check for local storage - load everything
			} else {
				// For non-local storage mode, apply limits
				if (!limit || limit >= 10000 || (this.items?.length >= 1000)) {
					console.log("Stopping background load: limit too high or too many items loaded", {
						limit,
						isNonLocalStorageMode,
						currentItemCount: this.items?.length || 0
					});
					return;
				}
			}
			
			// For non-local storage mode, use smaller batches
			// For local storage mode, use full batch size
			let effectiveLimit = isNonLocalStorageMode ? Math.min(limit, 200) : limit;
			
			console.log("Background loading items:", { 
				offset, 
				effectiveLimit, 
				isNonLocalStorageMode, 
				isLocalStorageMode,
				currentItemCount: this.items?.length || 0
			});
			
			const lastSync = syncSince;
			if (this.itemWorker) {
				try {
					const res = await fetch("/api/method/posawesome.posawesome.api.items.get_items", {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							"X-Frappe-CSRF-Token": frappe.csrf_token,
						},
						credentials: "same-origin",
						body: JSON.stringify({
							pos_profile: JSON.stringify(this.pos_profile),
							price_list: this.customer_price_list,
							item_group: this.item_group !== "ALL" ? this.item_group.toLowerCase() : "",
							search_value: this.search || "",
							customer: this.customer,
							modified_after: lastSync,
							limit: effectiveLimit,
							offset,
						}),
					});
					const text = await res.text();
					const count = await new Promise((resolve) => {
						// Check if itemWorker is still available
						if (!this.itemWorker) {
							console.warn("itemWorker is null, cannot process background items");
							resolve(0);
							return;
						}
						
						this.itemWorker.onmessage = (ev) => {
							if (ev.data.type === "parsed") {
								resolve(ev.data.items.length);
							} else if (ev.data.type === "error") {
								console.error("Item worker parse error:", ev.data.error);
								resolve(0);
							}
						};
						this.itemWorker.postMessage({
							type: "parse_and_cache",
							json: text,
							priceList: this.customer_price_list || "",
						});
					});
					if (count === effectiveLimit) {
						await this.backgroundLoadItems(offset + effectiveLimit, syncSince, clearBefore);
					} else {
						setItemsLastSync(new Date().toISOString());
						if (this.itemWorker) {
							this.itemWorker.terminate();
							this.itemWorker = null;
						}
						if (this.items && this.items.length > 0) {
							// Only cache stock for local storage mode
							if (this.pos_profile?.posa_local_storage) {
								await this.prePopulateStockCache(this.items);
							}
						}
					}
				} catch (err) {
					console.error("Failed to background load items", err);
				}
			} else {
				frappe.call({
					method: "posawesome.posawesome.api.items.get_items",
					args: {
						pos_profile: JSON.stringify(this.pos_profile),
						price_list: this.customer_price_list,
						item_group: this.item_group !== "ALL" ? this.item_group.toLowerCase() : "",
						search_value: this.search || "",
						customer: this.customer,
						modified_after: lastSync,
						limit: effectiveLimit,
						offset,
					},
					callback: async (r) => {
						const rows = r.message || [];
						rows.forEach((it) => {
							const existing = this.items.find((i) => i.item_code === it.item_code);
							if (existing) Object.assign(existing, it);
							else this.items.push(it);
						});
						this.eventBus.emit("set_all_items", this.items);
						if (
							this.pos_profile &&
							this.pos_profile.posa_local_storage &&
							!this.pos_profile.pose_use_limit_search
						) {
							if (clearBefore) {
								await clearStoredItems();
								clearBefore = false;
							}
							await saveItems(this.items);
						}
						if (rows.length === effectiveLimit) {
							this.backgroundLoadItems(offset + effectiveLimit, syncSince, clearBefore);
						} else {
							setItemsLastSync(new Date().toISOString());
							if (this.items && this.items.length > 0 && this.pos_profile?.posa_local_storage) {
								await this.prePopulateStockCache(this.items);
							}
						}
					},
					error: (err) => {
						console.error("Failed to background load items", err);
					},
				});
			}
		},
		get_items_groups() {
			if (!this.pos_profile) {
				console.error("get_items_groups: No POS Profile available");
				frappe.show_alert({
					message: __("POS Profile is not loaded. Please refresh the page."),
					indicator: "red"
				}, 5);
				return;
			}
			
			if (!this.pos_profile.name) {
				console.error("get_items_groups: POS Profile has no name:", this.pos_profile);
				frappe.show_alert({
					message: __("Invalid POS Profile. Please contact administrator."),
					indicator: "red"
				}, 5);
				return;
			}
			
			this.items_group = ["ALL"];
			if (this.pos_profile.item_groups.length > 0) {
				const groups = [];
				this.pos_profile.item_groups.forEach((element) => {
					if (element.item_group !== "All Item Groups") {
						this.items_group.push(element.item_group);
						groups.push(element.item_group);
					}
				});
				saveItemGroups(groups);
			} else if (isOffline()) {
				const cached = getCachedItemGroups();
				cached.forEach((g) => {
					this.items_group.push(g);
				});
			} else {
				const vm = this;
				frappe.call({
					method: "posawesome.posawesome.api.items.get_items_groups",
					args: {},
					callback: function (r) {
						if (r.message) {
							const groups = [];
							r.message.forEach((element) => {
								vm.items_group.push(element.name);
								groups.push(element.name);
							});
							saveItemGroups(groups);
						}
					},
				});
			}
		},
		getItemsHeaders() {
			const items_headers = [
				{
					title: __("Name"),
					align: "start",
					sortable: true,
					key: "item_name",
				},
				{
					title: __("Code"),
					align: "start",
					sortable: true,
					key: "item_code",
				},
				{ title: __("Rate"), key: "rate", align: "start" },
				{ title: __("Available QTY"), key: "actual_qty", align: "start" },
				{ title: __("UOM"), key: "stock_uom", align: "start" },
			];
			if (!this.pos_profile.posa_display_item_code) {
				items_headers.splice(1, 1);
			}

			return items_headers;
		},
		async click_item_row(event, { item }) {
			await this.add_item(item);
		},
		async add_item(item) {
			console.log("add_item called with:", item.item_code, "rate:", item.rate);
			item = { ...item };
			
			if (item.has_variants) {
				console.log("add_item: Item has variants, showing variant selection");
				let variants = this.items.filter((it) => it.variant_of == item.item_code);
				let attrsMeta = {};
				if (!variants.length) {
					try {
						const res = await frappe.call({
							method: "posawesome.posawesome.api.items.get_item_variants",
							args: {
								pos_profile: JSON.stringify(this.pos_profile),
								parent_item_code: item.item_code,
								price_list: this.active_price_list,
								customer: this.customer,
							},
						});
						if (res.message) {
							variants = res.message.variants || res.message;
							attrsMeta = res.message.attributes_meta || {};
							this.items.push(...variants);
						}
					} catch (e) {
						console.error("Failed to fetch variants", e);
					}
				}
				this.eventBus.emit("show_message", {
					title: __("This is an item template. Please choose a variant."),
					color: "warning",
				});
				console.log("sending profile", this.pos_profile);
				// Ensure attributes meta is always an object
				attrsMeta = attrsMeta || {};
				this.eventBus.emit("open_variants_model", item, variants, this.pos_profile, attrsMeta);
			} else {
				console.log("add_item: Adding regular item");
				
				if (item.actual_qty === 0 && this.pos_profile.posa_display_items_in_stock) {
					console.log("add_item: No stock available, showing warning");
					this.eventBus.emit("show_message", {
						title: `No stock available for ${item.item_name}`,
						color: "warning",
					});
					await this.update_items_details([item]);
					return;
				}

				// Ensure UOMs are initialized before adding the item
				if (!item.item_uoms || item.item_uoms.length === 0) {
					console.log("add_item: UOMs not available, fetching item details");
					// If UOMs are not available, fetch them first
					await this.update_items_details([item]);

					// Add stock UOM as fallback
					if (!item.item_uoms || item.item_uoms.length === 0) {
						item.item_uoms = [{ uom: item.stock_uom, conversion_factor: 1.0 }];
					}
				}

				// Ensure correct rate based on selected currency
				if (this.pos_profile.posa_allow_multi_currency) {
					console.log("add_item: Applying currency conversion");
					this.applyCurrencyConversionToItem(item);

					// Compute base rates from original values
					const base_rate =
						item.original_currency === this.pos_profile.currency
							? item.original_rate
							: item.original_rate * (item.plc_conversion_rate || this.exchange_rate);
					item.base_rate = base_rate;
					item.base_price_list_rate = base_rate;
				}

				if (!item.qty || item.qty === 1) {
					let qtyVal = this.qty != null ? this.qty : 1;
					qtyVal = Math.abs(qtyVal);
					if (this.hide_qty_decimals) {
						qtyVal = Math.trunc(qtyVal);
					}
					item.qty = qtyVal;
				}
				
				console.log("add_item: Emitting add_item event with item:", {
					item_code: item.item_code,
					item_name: item.item_name,
					rate: item.rate,
					qty: item.qty,
					actual_qty: item.actual_qty
				});
				
				this.eventBus.emit("add_item", item);
				this.qty = 1;
				console.log("add_item: Item addition completed");
			}
		},
		async enter_event() {
			let match = false;
			if (!this.filtered_items.length || !this.first_search) {
				return;
			}
			const qty = this.get_item_qty(this.first_search);
			const new_item = { ...this.filtered_items[0] };
			new_item.qty = flt(qty);
			new_item.item_barcode.forEach((element) => {
				if (this.search == element.barcode) {
					new_item.uom = element.posa_uom;
					match = true;
				}
			});
			if (
				!new_item.to_set_serial_no &&
				new_item.has_serial_no &&
				this.pos_profile.posa_search_serial_no
			) {
				new_item.serial_no_data.forEach((element) => {
					if (this.search && element.serial_no == this.search) {
						new_item.to_set_serial_no = this.first_search;
						match = true;
					}
				});
			}
			if (this.flags.serial_no) {
				new_item.to_set_serial_no = this.flags.serial_no;
			}
			if (!new_item.to_set_batch_no && new_item.has_batch_no && this.pos_profile.posa_search_batch_no) {
				new_item.batch_no_data.forEach((element) => {
					if (this.search && element.batch_no == this.search) {
						new_item.to_set_batch_no = this.first_search;
						new_item.batch_no = this.first_search;
						match = true;
					}
				});
			}
			if (this.flags.batch_no) {
				new_item.to_set_batch_no = this.flags.batch_no;
			}
			if (match) {
				await this.add_item(new_item);
				this.flags.serial_no = null;
				this.flags.batch_no = null;
				this.qty = 1;
				// Clear search field after successfully adding an item
				this.clearSearch();
				this.$refs.debounce_search.focus();
			}
		},
		reload_items_force() {
			console.log("Force reloading items...");
			// Clear cache and force server reload
			this.items = [];
			this.items_loaded = false;
			this.search_cache.clear();
			
			// Clear local storage cache if enabled
			if (this.pos_profile && this.pos_profile.posa_local_storage) {
				try {
					// Clear various cache keys
					const cacheKeys = [
						`items_${this.customer_price_list}`,
						`items_cache_${this.customer_price_list}`,
						'posawesome_items_last_sync'
					];
					cacheKeys.forEach(key => {
						localStorage.removeItem(key);
					});
				} catch (e) {
					console.error("Failed to clear localStorage cache:", e);
				}
			}
			
			// Show loading message
			frappe.show_alert({
				message: __("Reloading items..."),
				indicator: "blue"
			}, 3);
			
			// Force reload from server
			this.get_items(true);
		},
		// Debug method to check current state
		debugItemsState() {
			console.log("=== ITEMS DEBUG INFO ===");
			console.log("items_loaded:", this.items_loaded);
			console.log("items count:", this.items?.length || 0);
			console.log("filtered_items count:", this.filtered_items?.length || 0);
			console.log("loading:", this.loading);
			console.log("search_loading:", this.search_loading);
			console.log("search (first_search):", this.first_search);
			console.log("search (computed):", this.search);
			console.log("debounce_search:", this.debounce_search);
			console.log("pos_profile:", this.pos_profile?.name);
			console.log("customer_price_list:", this.customer_price_list);
			console.log("pose_use_limit_search:", this.pos_profile?.pose_use_limit_search);
			console.log("posa_local_storage:", this.pos_profile?.posa_local_storage);
			console.log("maxLocalStorageItems:", this.maxLocalStorageItems);
			console.log("Local storage usage:", `${this.items?.length || 0}/${this.maxLocalStorageItems}`);
			console.log("Local storage limit reached:", (this.items?.length || 0) >= this.maxLocalStorageItems);
			console.log("search_cache size:", this.search_cache?.size || 0);
			console.log("item_group:", this.item_group);
			console.log("itemsPerPage:", this.itemsPerPage);
			console.log("hide_zero_rate_items:", this.hide_zero_rate_items);
			
			// Show local storage limit status
			if (this.pos_profile?.posa_local_storage) {
				console.log("🏪 LOCAL STORAGE MODE ACTIVE");
				console.log("📊 Storage Status:", {
					current: this.items?.length || 0,
					limit: this.maxLocalStorageItems,
					percentage: Math.round(((this.items?.length || 0) / this.maxLocalStorageItems) * 100),
					withinLimit: (this.items?.length || 0) <= this.maxLocalStorageItems
				});
			} else {
				console.log("🌐 SERVER MODE ACTIVE - Local storage limit does not apply");
			}
			
			if (this.items && this.items.length > 0) {
				console.log("Sample items:", this.items.slice(0, 3));
			} else {
				console.log("No items found - this could be the issue!");
			}
			
			if (this.filtered_items && this.filtered_items.length > 0) {
				console.log("Sample filtered items:", this.filtered_items.slice(0, 3));
			} else {
				console.log("No filtered items - this is why you see 'No data available'");
			}
			
			// Check localStorage
			try {
				const cacheKey = `items_${this.customer_price_list}`;
				const cached = localStorage.getItem(cacheKey);
				console.log("localStorage cache exists:", !!cached);
				if (cached) {
					const parsedCache = JSON.parse(cached);
					console.log("localStorage items count:", parsedCache?.length || 0);
					console.log("localStorage size (bytes):", cached.length);
				}
			} catch (e) {
				console.log("localStorage check failed:", e.message);
			}
			
			console.log("========================");
		},
		
		// Test method to force items reload and check network
		async testItemsLoad() {
			console.log("=== TESTING ITEMS LOAD ===");
			
			try {
				// Clear all caches
				await forceClearAllCache();
				this.items = [];
				this.items_loaded = false;
				
				// Try to load items directly
				console.log("Attempting to load items...");
				const result = await this.get_items(true);
				
				console.log("Load result:", result);
				console.log("Items after load:", this.items ? this.items.length : "none");
				
				if (!this.items || this.items.length === 0) {
					console.warn("Items still not loaded. Checking network...");
					
					// Test network connectivity to the API
					try {
						const response = await frappe.call({
							method: "posawesome.posawesome.api.items.get_items",
							args: {
								pos_profile: JSON.stringify(this.pos_profile),
								price_list: this.pos_profile.selling_price_list,
								item_group: "",
								search_value: "",
								customer: this.customer,
								limit: 10,
								offset: 0,
							},
							freeze: false,
						});
						
						console.log("Direct API test result:", response);
						
						if (response && response.message) {
							console.log("API returned", response.message.length, "items");
							if (response.message.length > 0) {
								console.log("First API item:", response.message[0]);
							} else {
								console.warn("API returned empty array - this might be a data or permission issue");
							}
						} else {
							console.error("API returned no items or unexpected format");
						}
					} catch (api_error) {
						console.error("API test failed:", api_error);
					}
					
					// Test with different search parameters
					console.log("Testing with empty search parameters...");
					try {
						const emptySearchResponse = await frappe.call({
							method: "posawesome.posawesome.api.items.get_items", 
							args: {
								pos_profile: JSON.stringify(this.pos_profile),
								price_list: this.pos_profile.selling_price_list,
								item_group: "ALL",
								search_value: "",
								customer: this.customer || "",
								limit: 50,
								offset: 0,
							},
							freeze: false,
						});
						
						console.log("Empty search API result:", emptySearchResponse);
						if (emptySearchResponse && emptySearchResponse.message) {
							console.log("Empty search returned", emptySearchResponse.message.length, "items");
						}
					} catch (empty_search_error) {
						console.error("Empty search test failed:", empty_search_error);
					}
				}
				
			} catch (e) {
				console.error("Test load failed:", e);
			}
			
			console.log("=== END TEST ===");
		},
		async handleEnterKey() {
			console.log("handleEnterKey called with search:", this.first_search);
			
			// Handle Enter key press for item search
			if (!this.first_search || !this.first_search.trim()) {
				// If no search term but no items loaded, try force reload
				if (!this.items || this.items.length === 0) {
					console.log("No search term and no items loaded, forcing reload...");
					this.reload_items_force();
				}
				return;
			}

			// If there are filtered items, try to add the first one
			if (this.filtered_items && this.filtered_items.length > 0) {
				console.log("handleEnterKey: Found", this.filtered_items.length, "filtered items");
				console.log("handleEnterKey: First item:", this.filtered_items[0]);
				
				let match = false;
				const qty = this.get_item_qty(this.first_search);
				const new_item = { ...this.filtered_items[0] };
				new_item.qty = flt(qty || 1);
				
				console.log("handleEnterKey: Adding item with qty:", new_item.qty);
				
				// Check for exact barcode match
				if (Array.isArray(new_item.item_barcode)) {
					new_item.item_barcode.forEach((element) => {
						if (this.search == element.barcode) {
							new_item.uom = element.posa_uom;
							match = true;
							console.log("handleEnterKey: Barcode match found");
						}
					});
				}
				
				// Check for serial number match if enabled
				if (
					!new_item.to_set_serial_no &&
					new_item.has_serial_no &&
					this.pos_profile.posa_search_serial_no &&
					Array.isArray(new_item.serial_no_data)
				) {
					new_item.serial_no_data.forEach((element) => {
						if (this.search && element.serial_no == this.search) {
							new_item.to_set_serial_no = this.first_search;
							match = true;
							console.log("handleEnterKey: Serial number match found");
						}
					});
				}
				if (this.flags.serial_no) {
					new_item.to_set_serial_no = this.flags.serial_no;
				}
				
				// Check for batch number match if enabled
				if (!new_item.to_set_batch_no && new_item.has_batch_no && this.pos_profile.posa_search_batch_no && Array.isArray(new_item.batch_no_data)) {
					new_item.batch_no_data.forEach((element) => {
						if (this.search && element.batch_no == this.search) {
							new_item.to_set_batch_no = this.first_search;
							new_item.batch_no = this.first_search;
							match = true;
							console.log("handleEnterKey: Batch number match found");
						}
					});
				}
				if (this.flags.batch_no) {
					new_item.to_set_batch_no = this.flags.batch_no;
				}
				
				console.log("handleEnterKey: About to add item:", new_item.item_code, "with rate:", new_item.rate);
				
				// Add the item (either with exact match or just the first filtered item)
				try {
					await this.add_item(new_item);
					console.log("handleEnterKey: Item added successfully");
					
					// Reset flags after successful addition
					this.flags.serial_no = null;
					this.flags.batch_no = null;
					this.qty = 1;
					
					// Clear search field after successfully adding an item
					// Use a small delay to ensure the add_item event is fully processed
					setTimeout(() => {
						this.clearSearch();
						this.$refs.debounce_search && this.$refs.debounce_search.focus();
					}, 100);
					
				} catch (error) {
					console.error("handleEnterKey: Error adding item:", error);
					// Show error message but don't clear search so user can try again
					this.eventBus.emit("show_message", {
						title: `Error adding item "${new_item.item_name}": ${error.message}`,
						color: "error",
					});
				}
			} else {
				// No filtered items found
				console.log("handleEnterKey: No items found for search term:", this.first_search);
				
				// Show user-friendly message for item not found
				this.eventBus.emit("show_message", {
					title: `Item "${this.first_search}" not found`,
					color: "warning",
				});
				
				// For local storage mode, items are already loaded, just clear search
				if (this.pos_profile && this.pos_profile.posa_local_storage && this.items && this.items.length > 0) {
					console.log("handleEnterKey: Local storage mode - items loaded, just clearing search");
					// Don't reload items, just clear the search
				} else if (this.items && this.items.length > 0) {
					// Items are loaded but search didn't find anything
					this.search_onchange();
				} else {
					// No items loaded at all, force reload
					console.log("handleEnterKey: No items loaded, forcing reload...");
					this.reload_items_force();
				}
			}
		},
		search_onchange: _.debounce(function (newSearchTerm) {
			const vm = this;

			// Determine the actual query string and trim whitespace
			const query = typeof newSearchTerm === "string" ? newSearchTerm : vm.first_search;

			vm.search = (query || "").trim();

			if (!vm.search) {
				vm.search_from_scanner = false;
				// When search is cleared, ensure items are visible
				vm.ensureItemsVisible();
				return;
			}

			const fromScanner = vm.search_from_scanner;

			// Check if we should use dynamic loading for large datasets
			const shouldUseDynamicLoading = vm.dynamicLoadingConfig.enabled && 
				!vm.pos_profile?.posa_local_storage && 
				!vm.pos_profile?.pose_use_limit_search;

			if (shouldUseDynamicLoading && vm.search.length >= vm.dynamicLoadingConfig.searchThreshold) {
				console.log("Dynamic search triggered for:", vm.search);
				vm.loading = true;
				vm.loadItemsWithDynamicStrategy(vm.search, true).then(() => {
					vm.loading = false;
				}).catch((error) => {
					console.error("Dynamic search error:", error);
					vm.loading = false;
				});
				return;
			}

			if (vm.pos_profile && vm.pos_profile.pose_use_limit_search) {
				// Reduce minimum threshold to 2 characters for better usability
				// and allow single character search for item codes/barcodes
				const minLength = vm.search.match(/^[A-Z0-9\-_]+$/i) ? 1 : 2;
				if (vm.search && vm.search.length >= minLength) {
					if (vm.pos_profile && !vm.pos_profile.posa_local_storage) {
						vm.get_items(true);
					} else {
						vm.get_items();
					}
				}
			} else if (vm.pos_profile && vm.pos_profile.posa_local_storage) {
				// Don't reset items when doing local search - just let filtering work
				console.log("Local storage search - not calling loadVisibleItems");
				// The filtered_items computed property will handle the filtering
			} else {
				// Reduce minimum length for local search as well
				const minLength = vm.search.match(/^[A-Z0-9\-_]+$/i) ? 1 : 2;
				if (vm.search && vm.search.length >= minLength) {
					vm.enter_event();
				}

				// After search, update quantities for newly filtered items
				if (vm.filtered_items && vm.filtered_items.length > 0) {
					setTimeout(() => {
						vm.update_items_details(vm.filtered_items);
					}, 300);
				}
			}

			// Clear the input only when triggered via scanner
			if (fromScanner) {
				vm.clearSearch();
				vm.$refs.debounce_search && vm.$refs.debounce_search.focus();
				vm.search_from_scanner = false;
			}
		}, 250), // Reduce debounce time for faster response
		get_item_qty(first_search) {
			const qtyVal = this.qty != null ? this.qty : 1;
			let scal_qty = Math.abs(qtyVal);
			if (first_search.startsWith(this.pos_profile.posa_scale_barcode_start)) {
				let pesokg1 = first_search.substr(7, 5);
				let pesokg;
				if (pesokg1.startsWith("0000")) {
					pesokg = "0.00" + pesokg1.substr(4);
				} else if (pesokg1.startsWith("000")) {
					pesokg = "0.0" + pesokg1.substr(3);
				} else if (pesokg1.startsWith("00")) {
					pesokg = "0." + pesokg1.substr(2);
				} else if (pesokg1.startsWith("0")) {
					pesokg = pesokg1.substr(1, 1) + "." + pesokg1.substr(2, pesokg1.length);
				} else if (!pesokg1.startsWith("0")) {
					pesokg = pesokg1.substr(0, 2) + "." + pesokg1.substr(2, pesokg1.length);
				}
				scal_qty = pesokg;
			}
			if (this.hide_qty_decimals) {
				scal_qty = Math.trunc(scal_qty);
			}
			return scal_qty;
		},
		get_search(first_search) {
			let search_term = "";
			if (first_search && first_search.startsWith(this.pos_profile.posa_scale_barcode_start)) {
				search_term = first_search.substr(0, 7);
			} else {
				search_term = first_search;
			}
			return search_term;
		},
		esc_event() {
			this.search = null;
			this.first_search = null;
			this.search_backup = null;
			this.qty = 1;
			this.$refs.debounce_search.focus();
		},
		async update_items_details(items) {
			const vm = this;
			if (!items || !items.length) return;

			// reset any pending retry timer
			if (vm.itemDetailsRetryTimeout) {
				clearTimeout(vm.itemDetailsRetryTimeout);
				vm.itemDetailsRetryTimeout = null;
			}

			const itemCodes = items.map((it) => it.item_code);
			const cacheResult = getCachedItemDetails(vm.pos_profile.name, vm.active_price_list, itemCodes);
			cacheResult.cached.forEach((det) => {
				const item = items.find((it) => it.item_code === det.item_code);
				if (item) {
					Object.assign(item, {
						actual_qty: det.actual_qty,
						serial_no_data: det.serial_no_data,
						batch_no_data: det.batch_no_data,
						has_batch_no: det.has_batch_no,
						has_serial_no: det.has_serial_no,
					});
					if (det.item_uoms && det.item_uoms.length > 0) {
						item.item_uoms = det.item_uoms;
						saveItemUOMs(item.item_code, det.item_uoms);
					}
					if (det.rate !== undefined) {
						if (det.rate !== 0 || !item.rate) {
							item.rate = det.rate;
							item.price_list_rate = det.price_list_rate || det.rate;
						}
					}

					if (!item.original_rate) {
						item.original_rate = item.rate;
						item.original_currency = item.currency || vm.pos_profile.currency;
					}

					vm.applyCurrencyConversionToItem(item);
				}
			});

			let allCached = cacheResult.missing.length === 0;
			items.forEach((item) => {
				const localQty = getLocalStock(item.item_code);
				if (localQty !== null) {
					item.actual_qty = localQty;
				} else {
					allCached = false;
				}

				if (!item.item_uoms || item.item_uoms.length === 0) {
					const cachedUoms = getItemUOMs(item.item_code);
					if (cachedUoms.length > 0) {
						item.item_uoms = cachedUoms;
					} else if (isOffline()) {
						item.item_uoms = [{ uom: item.stock_uom, conversion_factor: 1.0 }];
					} else {
						allCached = false;
					}
				}
			});

			// When offline or everything is cached, skip server call
			if (isOffline() || allCached) {
				vm.itemDetailsRetryCount = 0;
				return;
			}

			// Cancel previous request
			if (vm.currentRequest) {
				vm.abortController.abort();
				vm.currentRequest = null;
			}

			vm.abortController = new AbortController();

			const itemsToFetch = items.filter(
				(it) => cacheResult.missing.includes(it.item_code) && !it.has_variants,
			);

			if (itemsToFetch.length === 0) {
				vm.itemDetailsRetryCount = 0;
				return;
			}

			try {
				vm.currentRequest = await frappe.call({
					method: "posawesome.posawesome.api.items.get_items_details",
					args: {
						pos_profile: JSON.stringify(vm.pos_profile),
						items_data: JSON.stringify(itemsToFetch),
						price_list: vm.active_price_list,
					},
					freeze: false,
					signal: vm.abortController.signal,
				});

				const r = vm.currentRequest;
				if (r && r.message) {
					vm.itemDetailsRetryCount = 0;
					let qtyChanged = false;
					let updatedItems = [];

					items.forEach((item) => {
						const updated_item = r.message.find((element) => element.item_code == item.item_code);
						if (updated_item) {
							const prev_qty = item.actual_qty;

							updatedItems.push({
								item: item,
								updates: {
									actual_qty: updated_item.actual_qty,
									serial_no_data: updated_item.serial_no_data,
									batch_no_data: updated_item.batch_no_data,
									has_batch_no: updated_item.has_batch_no,
									has_serial_no: updated_item.has_serial_no,
									item_uoms:
										updated_item.item_uoms && updated_item.item_uoms.length > 0
											? updated_item.item_uoms
											: item.item_uoms,
								},
							});

							if (prev_qty > 0 && updated_item.actual_qty === 0) {
								qtyChanged = true;
							}

							if (updated_item.item_uoms && updated_item.item_uoms.length > 0) {
								saveItemUOMs(item.item_code, updated_item.item_uoms);
							}
						}
					});

					updatedItems.forEach(({ item, updates }) => {
						Object.assign(item, updates);
						vm.applyCurrencyConversionToItem(item);
					});

					updateLocalStockCache(r.message);
					saveItemDetailsCache(vm.pos_profile.name, vm.active_price_list, r.message);

					if (qtyChanged) {
						vm.$forceUpdate();
					}
				}
			} catch (err) {
				if (err.name !== "AbortError") {
					console.error("Error fetching item details:", err);
					items.forEach((item) => {
						const localQty = getLocalStock(item.item_code);
						if (localQty !== null) {
							item.actual_qty = localQty;
						}
						if (!item.item_uoms || item.item_uoms.length === 0) {
							const cached = getItemUOMs(item.item_code);
							if (cached.length > 0) {
								item.item_uoms = cached;
							}
						}
					});

					if (!isOffline()) {
						vm.itemDetailsRetryCount += 1;
						const delay = Math.min(32000, 1000 * Math.pow(2, vm.itemDetailsRetryCount - 1));
						vm.itemDetailsRetryTimeout = setTimeout(() => {
							vm.update_items_details(items);
						}, delay);
					}
				}
			}

			// Cleanup on component destroy
			this.cleanupBeforeDestroy = () => {
				if (vm.abortController) {
					vm.abortController.abort();
				}
			};
		},
		update_cur_items_details() {
			if (this.filtered_items && this.filtered_items.length > 0) {
				this.update_items_details(this.filtered_items);
			}
		},
		async prePopulateStockCache(items) {
			if (this.prePopulateInProgress) {
				return;
			}
			if (!Array.isArray(items) || items.length === 0) {
				return;
			}
			this.prePopulateInProgress = true;
			try {
				const cache = getLocalStockCache();
				const cacheSize = Object.keys(cache).length;

				if (isStockCacheReady() && cacheSize >= items.length) {
					console.debug("Stock cache already initialized");
					return;
				}

				if (items.length > 500) {
					console.info("Pre-populating stock cache for", items.length, "items in batches");
				} else {
					console.info("Pre-populating stock cache for", items.length, "items");
				}

				await initializeStockCache(items, this.pos_profile);
			} catch (error) {
				console.error("Failed to pre-populate stock cache:", error);
			} finally {
				this.prePopulateInProgress = false;
			}
		},

		applyCurrencyConversionToItems() {
			if (!this.items || !this.items.length) return;
			this.items.forEach((it) => this.applyCurrencyConversionToItem(it));
		},

		applyCurrencyConversionToItem(item) {
			if (!item) return;
			const base = this.pos_profile.currency;

			if (!item.original_rate) {
				item.original_rate = item.rate;
				item.original_currency = item.currency || base;
			}

			// original_rate is in price list currency
			const price_list_rate = item.original_rate;

			// Determine base rate using available conversion info
			const base_rate = price_list_rate * (item.plc_conversion_rate || 1);

			item.base_rate = base_rate;
			item.base_price_list_rate = price_list_rate;

			// If the price list currency matches the selected currency,
			// don't apply any conversion
			const converted_rate =
				item.original_currency === this.selected_currency
					? price_list_rate
					: price_list_rate * (this.exchange_rate || 1);

			item.rate = this.flt(converted_rate, this.currency_precision);
			item.currency = this.selected_currency;
			item.price_list_rate = item.rate;
		},
		scan_barcoud() {
			const vm = this;
			try {
				// Check if scanner is already attached to document
				if (document._scannerAttached) {
					return;
				}

				// Check if onScan library is available
				if (typeof onScan === 'undefined') {
					console.warn("onScan library not available - barcode scanning disabled");
					return;
				}

				onScan.attachTo(document, {
					suffixKeyCodes: [],
					keyCodeMapper: function (oEvent) {
						oEvent.stopImmediatePropagation();
						oEvent.preventDefault();
						return onScan.decodeKeyEvent(oEvent);
					},
					onScan: function (sCode) {
						setTimeout(() => {
							vm.trigger_onscan(sCode);
						}, 300);
					},
				});

				// Mark document as having scanner attached
				document._scannerAttached = true;
			} catch (error) {
				console.warn("Scanner initialization error:", error.message);
			}
		},
		trigger_onscan(sCode) {
			// indicate this search came from a scanner
			this.search_from_scanner = true;
			// apply scanned code as search term
			this.first_search = sCode;
			this.search = sCode;

			this.$nextTick(() => {
				if (this.filtered_items.length == 0) {
					this.eventBus.emit("show_message", {
						title: `No Item has this barcode "${sCode}"`,
						color: "error",
					});
					frappe.utils.play_sound("error");
				} else {
					this.enter_event();
				}

				// clear search field for next scan and refocus input
				this.clearSearch();
				this.$refs.debounce_search && this.$refs.debounce_search.focus();
			});
		},
		generateWordCombinations(inputString) {
			const words = inputString.split(" ");
			const wordCount = words.length;
			const combinations = [];

			// Helper function to generate all permutations
			function permute(arr, m = []) {
				if (arr.length === 0) {
					combinations.push(m.join(" "));
				} else {
					for (let i = 0; i < arr.length; i++) {
						const current = arr.slice();
						const next = current.splice(i, 1);
						permute(current.slice(), m.concat(next));
					}
				}
			}

			permute(words);

			return combinations;
		},
		// Method to ensure items are properly displayed after operations
		ensureItemsVisible() {
			console.log("ensureItemsVisible called");
			console.log("Current state: items:", this.items?.length || 0, "filtered_items:", this.filtered_items?.length || 0, "items_loaded:", this.items_loaded);
			
			// If no items are loaded at all, trigger initial load
			if (!this.items_loaded || !this.items || this.items.length === 0) {
				console.log("ensureItemsVisible: No items loaded, triggering reload from server");
				this.get_items(true); // Force server load when no items exist
				return;
			}
			
			// If items exist but aren't showing in filtered_items after search is cleared
			if (this.items.length > 0 && (!this.filtered_items || this.filtered_items.length === 0) && !this.first_search) {
				console.log("ensureItemsVisible: Items exist but filtered_items empty with no search, forcing update");
				this.$forceUpdate();
				
				// Check again after a short delay and force rebuild if needed
				setTimeout(() => {
					if ((!this.filtered_items || this.filtered_items.length === 0) && !this.first_search) {
						console.log("ensureItemsVisible: Still no filtered items after delay, triggering view refresh");
						// Force trigger the computed property to recalculate
						this.$nextTick(() => {
							if (this.pos_profile && this.pos_profile.posa_local_storage) {
								this.loadVisibleItems(false);
							} else {
								this.$forceUpdate();
							}
						});
					}
				}, 200);
			}
		},

		forceItemsReload() {
			console.log("forceItemsReload called - forcing complete item reload");
			this.items = [];
			this.items_loaded = false;
			this.search_cache.clear();
			this.loadVisibleItems();
		},

		clearSearch() {
			console.log("clearSearch called - current state:", {
				first_search: this.first_search,
				search: this.search,
				local_storage_mode: this.is_local_storage_mode,
				items_length: this.items?.length || 0
			});
			
			this.search_backup = this.first_search;
			this.first_search = "";
			this.search = "";
			
			// Use nextTick to ensure the search clearing is processed first
			this.$nextTick(() => {
				console.log("clearSearch nextTick - after clearing:", {
					first_search: this.first_search,
					search: this.search,
					filtered_items_length: this.filtered_items?.length || 0,
					items_length: this.items?.length || 0
				});
				
				// Check if we need to reload items (especially in local storage mode)
				if (!this.items || this.items.length === 0) {
					console.log("clearSearch - calling ensureItemsVisible because no items");
					this.ensureItemsVisible();
				} else {
					console.log("clearSearch - items available, checking if they display correctly");
					
					// Add a timeout to verify items actually appear after clear
					setTimeout(() => {
						if ((!this.filtered_items || this.filtered_items.length === 0) && !this.first_search) {
							console.log("clearSearch timeout - items not showing after clear, forcing reload");
							this.forceItemsReload();
						}
					}, 300);
				}
			});
		},

		restoreSearch() {
			if (this.first_search === "") {
				this.first_search = this.search_backup;
				this.search = this.search_backup;
				// No need to reload items when focus is lost
			}
		},
		handleItemSearchFocus() {
			this.first_search = "";
			this.search = "";
			// Optionally, you might want to also clear search_backup if the behaviour should be a full reset on focus
			// this.search_backup = "";
		},

		clearQty() {
			this.qty = null;
		},

		startCameraScanning() {
			if (this.$refs.cameraScanner) {
				this.$refs.cameraScanner.startScanning();
			}
		},
		onBarcodeScanned(scannedCode) {
			console.log("Barcode scanned:", scannedCode);

			// mark this search as coming from a scanner
			this.search_from_scanner = true;

			// Clear any previous search
			this.search = "";
			this.first_search = "";

			// Set the scanned code as search term
			this.first_search = scannedCode;
			this.search = scannedCode;

			// Show scanning feedback
			frappe.show_alert(
				{
					message: `Scanning for: ${scannedCode}`,
					indicator: "blue",
				},
				2,
			);

			// Enhanced item search and submission logic
			setTimeout(() => {
				this.processScannedItem(scannedCode);
			}, 300);
		},
		processScannedItem(scannedCode) {
			// First try to find exact match by barcode
			let foundItem = this.items.find(
				(item) =>
					item.barcode === scannedCode ||
					item.item_code === scannedCode ||
					(item.barcodes && item.barcodes.some((bc) => bc.barcode === scannedCode)),
			);

			if (foundItem) {
				console.log("Found item by exact match:", foundItem);
				this.addScannedItemToInvoice(foundItem, scannedCode);
				return;
			}

			// If no exact match, try partial search
			const searchResults = this.searchItemsByCode(scannedCode);

			if (searchResults.length === 1) {
				console.log("Found item by search:", searchResults[0]);
				this.addScannedItemToInvoice(searchResults[0], scannedCode);
			} else if (searchResults.length > 1) {
				// Multiple matches - show selection dialog
				this.showMultipleItemsDialog(searchResults, scannedCode);
			} else {
				// No matches found
				this.handleItemNotFound(scannedCode);
			}
		},
		searchItemsByCode(code) {
			return this.items.filter((item) => {
				const searchTerm = code.toLowerCase();
				return (
					item.item_code.toLowerCase().includes(searchTerm) ||
					item.item_name.toLowerCase().includes(searchTerm) ||
					(item.barcode && item.barcode.toLowerCase().includes(searchTerm)) ||
					(item.barcodes &&
						item.barcodes.some((bc) => bc.barcode.toLowerCase().includes(searchTerm)))
				);
			});
		},
		async addScannedItemToInvoice(item, scannedCode) {
			console.log("Adding scanned item to invoice:", item, scannedCode);

			// Clone the item to avoid mutating list data
			const newItem = { ...item };

			// If the scanned barcode has a specific UOM, apply it
			if (Array.isArray(newItem.item_barcode)) {
				const barcodeMatch = newItem.item_barcode.find((b) => b.barcode === scannedCode);
				if (barcodeMatch && barcodeMatch.posa_uom) {
					newItem.uom = barcodeMatch.posa_uom;

					// Try fetching the rate for this UOM from the active price list
					try {
						const res = await frappe.call({
							method: "posawesome.posawesome.api.items.get_price_for_uom",
							args: {
								item_code: newItem.item_code,
								price_list: this.active_price_list,
								uom: barcodeMatch.posa_uom,
							},
						});
						if (res.message) {
							const price = parseFloat(res.message);
							newItem.rate = price;
							newItem.price_list_rate = price;
							newItem.base_rate = price;
							newItem.base_price_list_rate = price;
							newItem._manual_rate_set = true;
							newItem.skip_force_update = true;
						}
					} catch (e) {
						console.error("Failed to fetch UOM price", e);
					}
				}
			}

			// Use existing add_item method with enhanced feedback
			await this.add_item(newItem);

			// Show success message
			frappe.show_alert(
				{
					message: `Added: ${item.item_name}`,
					indicator: "green",
				},
				3,
			);

			// Clear search after successful addition and refocus input
			this.clearSearch();
			this.$refs.debounce_search && this.$refs.debounce_search.focus();
		},
		showMultipleItemsDialog(items, scannedCode) {
			// Create a dialog to let user choose from multiple matches
			const dialog = new frappe.ui.Dialog({
				title: __("Multiple Items Found"),
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "items_html",
						options: this.generateItemSelectionHTML(items, scannedCode),
					},
				],
				primary_action_label: __("Cancel"),
				primary_action: () => dialog.hide(),
			});

			dialog.show();

			// Add click handlers for item selection
			setTimeout(() => {
				items.forEach((item, index) => {
					const button = dialog.$wrapper.find(`[data-item-index="${index}"]`);
					button.on("click", () => {
						this.addScannedItemToInvoice(item, scannedCode);
						dialog.hide();
					});
				});
			}, 100);
		},
		generateItemSelectionHTML(items, scannedCode) {
			let html = `<div class="mb-3"><strong>Scanned Code:</strong> ${scannedCode}</div>`;
			html += '<div class="item-selection-list">';

			items.forEach((item, index) => {
				html += `
          <div class="item-option p-3 mb-2 border rounded cursor-pointer" data-item-index="${index}" style="border: 1px solid #ddd; cursor: pointer;">
            <div class="d-flex align-items-center">
              <img src="${item.image || "/assets/posawesome/js/posapp/components/pos/placeholder-image.png"}"
                   style="width: 50px; height: 50px; object-fit: cover; margin-right: 15px;" />
              <div>
                <div class="font-weight-bold">${item.item_name}</div>
                <div class="text-muted small">${item.item_code}</div>
                <div class="text-primary">${this.format_currency(item.rate, this.pos_profile.currency, this.ratePrecision(item.rate))}</div>
              </div>
            </div>
          </div>
        `;
			});

			html += "</div>";
			return html;
		},
		handleItemNotFound(scannedCode) {
			console.warn("Item not found for scanned code:", scannedCode);

			// Show error message
			frappe.show_alert(
				{
					message: `Item not found: ${scannedCode}`,
					indicator: "red",
				},
				5,
			);

			// Keep the search term for manual search
			this.trigger_onscan(scannedCode);
		},

		currencySymbol(currency) {
			return get_currency_symbol(currency);
		},
		format_currency(value, currency, precision) {
			const prec = typeof precision === "number" ? precision : this.currency_precision;
			return this.formatCurrency(value, prec);
		},
		ratePrecision(value) {
			const numericValue = typeof value === "string" ? parseFloat(value) : value;
			return Number.isInteger(numericValue) ? 0 : this.currency_precision;
		},
		format_number(value, precision) {
			const prec = typeof precision === "number" ? precision : this.float_precision;
			return this.formatFloat(value, prec);
		},
		hasDecimalPrecision(value) {
			// Check if the value has any decimal precision when converted by exchange rate
			if (this.exchange_rate && this.exchange_rate !== 1) {
				let convertedValue = value * this.exchange_rate;
				return !Number.isInteger(convertedValue);
			}
			return !Number.isInteger(value);
		},

		toggleItemSettings() {
			this.temp_hide_qty_decimals = this.hide_qty_decimals;
			this.temp_hide_zero_rate_items = this.hide_zero_rate_items;
			this.temp_enable_custom_items_per_page = this.enable_custom_items_per_page;
			this.temp_items_per_page = this.items_per_page;
			this.show_item_settings = true;
		},
		cancelItemSettings() {
			this.show_item_settings = false;
		},
		applyItemSettings() {
			this.hide_qty_decimals = this.temp_hide_qty_decimals;
			this.hide_zero_rate_items = this.temp_hide_zero_rate_items;
			this.enable_custom_items_per_page = this.temp_enable_custom_items_per_page;
			if (this.enable_custom_items_per_page) {
				this.items_per_page = parseInt(this.temp_items_per_page) || 50;
			} else {
				this.items_per_page = 50;
			}
			this.itemsPerPage = this.items_per_page;
			this.saveItemSettings();
			this.show_item_settings = false;
		},
		onDragStart(event, item) {
			this.isDragging = true;

			// Set drag data
			event.dataTransfer.setData(
				"application/json",
				JSON.stringify({
					type: "item-from-selector",
					item: item,
				}),
			);

			// Set drag effect
			event.dataTransfer.effectAllowed = "copy";

			// Emit event to show drop feedback in ItemsTable
			this.eventBus.emit("item-drag-start", item);
		},
		onDragEnd(event) {
			this.isDragging = false;

			// Emit event to hide drop feedback
			this.eventBus.emit("item-drag-end");
		},
		saveItemSettings() {
			try {
				const settings = {
					hide_qty_decimals: this.hide_qty_decimals,
					hide_zero_rate_items: this.hide_zero_rate_items,
					enable_custom_items_per_page: this.enable_custom_items_per_page,
					items_per_page: this.items_per_page,
				};
				localStorage.setItem("posawesome_item_selector_settings", JSON.stringify(settings));
			} catch (e) {
				console.error("Failed to save item selector settings:", e);
			}
		},
		loadItemSettings() {
			try {
				const saved = localStorage.getItem("posawesome_item_selector_settings");
				if (saved) {
					const opts = JSON.parse(saved);
					if (typeof opts.hide_qty_decimals === "boolean") {
						this.hide_qty_decimals = opts.hide_qty_decimals;
					}
					if (typeof opts.hide_zero_rate_items === "boolean") {
						this.hide_zero_rate_items = opts.hide_zero_rate_items;
					}
					if (typeof opts.enable_custom_items_per_page === "boolean") {
						this.enable_custom_items_per_page = opts.enable_custom_items_per_page;
					}
					if (typeof opts.items_per_page === "number") {
						this.items_per_page = opts.items_per_page;
						this.itemsPerPage = this.items_per_page;
					}
				}
			} catch (e) {
				console.error("Failed to load item selector settings:", e);
			}
		},
		
		async waitForPosProfile(maxWaitTime = 10000) {
			// If POS profile is already available, return immediately
			if (this.pos_profile && this.pos_profile.name) {
				return true;
			}
			
			console.log("Waiting for POS Profile to be available...");
			
			return new Promise((resolve, reject) => {
				let attempts = 0;
				const maxAttempts = maxWaitTime / 100; // Check every 100ms
				
				const checkProfile = () => {
					attempts++;
					
					if (this.pos_profile && this.pos_profile.name) {
						console.log("POS Profile is now available:", this.pos_profile.name);
						resolve(true);
						return;
					}
					
					if (attempts >= maxAttempts) {
						console.error("Timeout waiting for POS Profile");
						reject(new Error("Timeout waiting for POS Profile"));
						return;
					}
					
					setTimeout(checkProfile, 100);
				};
				
				checkProfile();
			});
		},
	},

	computed: {
		headers() {
			return this.getItemsHeaders();
		},
		filtered_items() {
			this.search = this.get_search(this.first_search).trim();
			
			// Debug logging to understand the issue
			if (!this.items || this.items.length === 0) {
				console.warn("filtered_items: No items available. items:", this.items?.length || 0, "items_loaded:", this.items_loaded);
				// If no items are loaded, trigger server load based on mode
				if (this.items_loaded === false || !this.items) {
					// Don't trigger reload in computed property - just return empty array
					// But log that we need items
					if (!this.items_loaded) {
						console.log("filtered_items: No items loaded - need server reload");
						// Use nextTick to avoid infinite reactivity loop
						this.$nextTick(() => {
							if (!this.items || this.items.length === 0) {
								console.log("filtered_items: Triggering server reload for empty items");
								// For non-local storage mode, use pagination-friendly load
								const isNonLocalStorageMode = !this.pos_profile?.posa_local_storage;
								this.get_items(isNonLocalStorageMode);
							}
						});
					}
					return [];
				}
			}

			let items = this.items || [];
			
			// For large datasets in non-local storage mode, implement virtual scrolling/pagination
			const isNonLocalStorageMode = !this.pos_profile?.posa_local_storage;
			if (isNonLocalStorageMode && items.length > 1000 && !this.search) {
				// Show only first batch when no search to prevent hanging
				items = items.slice(0, this.itemsPerPage || 50);
				console.log("filtered_items: Limited items for non-local storage mode:", items.length);
			}
			
			// Apply filtering based on search and item group
			if (!this.pos_profile || !this.pos_profile.pose_use_limit_search) {
				// Check search cache first for performance
				const cache_key = `${this.search}|${this.item_group}|${this.hide_zero_rate_items}|${this.itemsPerPage}`;
				if (this.search && this.search_cache.has(cache_key)) {
					return this.search_cache.get(cache_key);
				}
				
				let filtred_list = [];
				let filtred_group_list = [];
				
				// Ensure we have items to work with
				if (!items || items.length === 0) {
					console.warn("filtered_items: items array is empty or null");
					return [];
				}
				
				if (this.item_group != "ALL") {
					filtred_group_list = items.filter((item) =>
						item.item_group.toLowerCase().includes(this.item_group.toLowerCase()),
					);
				} else {
					filtred_group_list = items;
				}
				
				// When there's no search term, always show items (this is key for the clearSearch issue)
				if (!this.search || this.search.length === 0) {
					let filtered = [];
					if (
						this.pos_profile.posa_show_template_items &&
						this.pos_profile.posa_hide_variants_items
					) {
						filtered = filtred_group_list
							.filter((item) => !item.variant_of)
							.slice(0, this.itemsPerPage);
					} else {
						filtered = filtred_group_list.slice(0, this.itemsPerPage);
					}

					if (this.hide_zero_rate_items) {
						filtered = filtered.filter((item) => parseFloat(item.rate) !== 0);
					}

					// Ensure quantities are defined
					filtered.forEach((item) => {
						if (item.actual_qty === undefined) {
							item.actual_qty = 0;
						}
					});

					console.log("filtered_items: Returning", filtered.length, "items for empty search");
					return filtered;
				}
				
				// Reduce minimum search length for better UX with large datasets  
				const minSearchLength = this.search && this.search.match(/^[A-Z0-9\-_]+$/i) ? 1 : 2;
				
				if (this.search.length < minSearchLength) {
					// Still show items even if search is too short (but different from empty search)
					let filtered = [];
					if (
						this.pos_profile.posa_show_template_items &&
						this.pos_profile.posa_hide_variants_items
					) {
						filtered = filtred_group_list
							.filter((item) => !item.variant_of)
							.slice(0, this.itemsPerPage);
					} else {
						filtered = filtred_group_list.slice(0, this.itemsPerPage);
					}

					if (this.hide_zero_rate_items) {
						filtered = filtered.filter((item) => parseFloat(item.rate) !== 0);
					}

					// Ensure quantities are defined
					filtered.forEach((item) => {
						if (item.actual_qty === undefined) {
							item.actual_qty = 0;
						}
					});

					return filtered;
				} else if (this.search) {
					const term = this.search.toLowerCase();
					
					// Optimized search algorithm for large datasets
					// 1. First: Exact item code match (highest priority)
					filtred_list = filtred_group_list.filter((item) =>
						item.item_code.toLowerCase() === term
					);
					
					// 2. Second: Exact barcode match
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_barcode.some((b) => b.barcode === this.search)
						);
					}
					
					// 3. Third: Item code starts with search term
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_code.toLowerCase().startsWith(term)
						);
					}
					
					// 4. Fourth: Item name starts with search term
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_name.toLowerCase().startsWith(term)
						);
					}

					// 5. Fifth: Item code contains search term
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_code.toLowerCase().includes(term)
						);
					}
					
					// 6. Sixth: Item name contains search term
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_name.toLowerCase().includes(term)
						);
					}

					// 7. Seventh: Barcode contains search term
					if (filtred_list.length === 0) {
						filtred_list = filtred_group_list.filter((item) =>
							item.item_barcode.some((b) => b.barcode.toLowerCase().includes(term))
						);
					}

					// 8. Eighth: Serial number search (if enabled)
					if (filtred_list.length === 0 && this.pos_profile.posa_search_serial_no) {
						filtred_list = filtred_group_list.filter((item) => {
							return item.serial_no_data && item.serial_no_data.some((element) => {
								if (element.serial_no === this.search) {
									this.flags.serial_no = this.search;
									return true;
								}
								return false;
							});
						});
					}

					// 9. Ninth: Batch number search (if enabled)
					if (filtred_list.length === 0 && this.pos_profile.posa_search_batch_no) {
						filtred_list = filtred_group_list.filter((item) => {
							return item.batch_no_data && item.batch_no_data.some((element) => {
								if (element.batch_no === this.search) {
									this.flags.batch_no = this.search;
									return true;
								}
								return false;
							});
						});
					}
					
					// 10. Last resort: Fuzzy search (only for longer terms to avoid performance issues)
					if (filtred_list.length === 0 && this.search.length >= 3) {
						const search_combinations = this.generateWordCombinations(this.search);
						filtred_list = filtred_group_list.filter((item) => {
							const nameLower = item.item_name.toLowerCase();
							return search_combinations.some((element) => {
								element = element.toLowerCase().trim();
								const element_regex = new RegExp(`.*${element.split("").join(".*")}.*`);
								return element_regex.test(nameLower);
							});
						});
					}
				}

				let final_filtered_list = [];
				if (this.pos_profile.posa_show_template_items && this.pos_profile.posa_hide_variants_items) {
					final_filtered_list = filtred_list
						.filter((item) => !item.variant_of)
						.slice(0, this.itemsPerPage);
				} else {
					final_filtered_list = filtred_list.slice(0, this.itemsPerPage);
				}

				if (this.hide_zero_rate_items) {
					final_filtered_list = final_filtered_list.filter((item) => parseFloat(item.rate) !== 0);
				}

				// Ensure quantities are defined for each item
				final_filtered_list.forEach((item) => {
					if (item.actual_qty === undefined) {
						item.actual_qty = 0;
					}
				});

				// Cache the result for better performance
				if (this.search && final_filtered_list.length > 0) {
					// Limit cache size to prevent memory issues
					if (this.search_cache.size >= this.search_cache_max_size) {
						const firstKey = this.search_cache.keys().next().value;
						this.search_cache.delete(firstKey);
					}
					this.search_cache.set(cache_key, final_filtered_list);
				}

				return final_filtered_list;
			} else {
				const items_list = this.items.slice(0, this.itemsPerPage);

				// Ensure quantities are defined
				items_list.forEach((item) => {
					if (item.actual_qty === undefined) {
						item.actual_qty = 0;
					}
				});

				if (this.hide_zero_rate_items) {
					return items_list.filter((item) => parseFloat(item.rate) !== 0);
				}

				return items_list;
			}
		},
		debounce_search: {
			get() {
				return this.first_search;
			},
			set: _.debounce(function (newValue) {
				this.first_search = (newValue || "").trim();
			}, 150), // Reduced from 200ms for faster response
		},
		debounce_qty: {
			get() {
				// Display the raw quantity while typing to avoid forced decimal format
				if (this.qty === null || this.qty === "") return "";
				return this.hide_qty_decimals ? Math.trunc(this.qty) : this.qty;
			},
			set: _.debounce(function (value) {
				let parsed = parseFloat(String(value).replace(/,/g, ""));
				if (isNaN(parsed)) {
					parsed = null;
				}
				if (this.hide_qty_decimals && parsed != null) {
					parsed = Math.trunc(parsed);
				}
				this.qty = parsed;
			}, 200),
		},
		isDarkTheme() {
			return this.$theme.current === "dark";
		},
		active_price_list() {
			return this.customer_price_list || (this.pos_profile && this.pos_profile.selling_price_list);
		},
	},

	created() {
		memoryInitPromise.then(async () => {
			const profile = await ensurePosProfile();
			if (profile) {
				// Adjust page limit based on local storage setting
				this.itemsPageLimit = profile.posa_local_storage ? this.maxLocalStorageItems : 10000;
				if (profile.posa_local_storage) {
					this.loadVisibleItems(true);
				} else {
					await forceClearAllCache();
					await this.get_items(true);
				}
			}
		});

		this.loadItemSettings();
		if (typeof Worker !== "undefined") {
			try {
				// Use the plain URL so the service worker can match the cached file
				// even when offline. Using a query string causes cache lookups to fail
				// which results in "Failed to fetch a worker script" errors.
				const workerUrl = "/assets/posawesome/js/posapp/workers/itemWorker.js";
				this.itemWorker = new Worker(workerUrl, { type: "classic" });

				this.itemWorker.onerror = function (event) {
					console.error("Worker error:", event);
					console.error("Message:", event.message);
					console.error("Filename:", event.filename);
					console.error("Line number:", event.lineno);
				};
				console.log("Created worker nowwwwww");
			} catch (e) {
				console.error("Failed to start item worker", e);
				this.itemWorker = null;
			}
		}
		this.$nextTick(function () {});
		this.eventBus.on("register_pos_profile", async (data) => {
			await initPromise;
			await memoryInitPromise;
			await checkDbHealth();
			this.pos_profile = data.pos_profile;
			// Update page limit whenever profile is registered
			this.itemsPageLimit = this.pos_profile.posa_local_storage ? this.maxLocalStorageItems : 10000;
			if (!this.pos_profile.posa_local_storage) {
				await forceClearAllCache();
				await this.get_items(true);
			} else if (this.pos_profile.posa_force_reload_items && !this.pos_profile.posa_smart_reload_mode) {
				if (!isOffline()) {
					await this.get_items(true);
				} else {
					await this.get_items();
				}
			} else {
				await this.get_items();
			}
			this.get_items_groups();
			this.items_view = this.pos_profile.posa_default_card_view ? "card" : "list";
		});
		this.eventBus.on("update_cur_items_details", () => {
			this.update_cur_items_details();
		});
		this.eventBus.on("update_offers_counters", (data) => {
			this.offersCount = data.offersCount;
			this.appliedOffersCount = data.appliedOffersCount;
		});
		this.eventBus.on("update_coupons_counters", (data) => {
			this.couponsCount = data.couponsCount;
			this.appliedCouponsCount = data.appliedCouponsCount;
		});
		this.eventBus.on("update_customer_price_list", (data) => {
			this.customer_price_list = data;
		});
		this.eventBus.on("update_customer", (data) => {
			this.customer = data;
		});

		// Manually trigger a full item reload when requested
		this.eventBus.on("force_reload_items", async () => {
			this.items_loaded = false;
			if (!isOffline()) {
				if (this.pos_profile && !this.pos_profile.posa_local_storage) {
					await forceClearAllCache();
				}
				await this.get_items(true);
			} else {
				if (this.pos_profile && !this.pos_profile.posa_local_storage) {
					await forceClearAllCache();
					await this.get_items(true);
				} else {
					await this.get_items();
				}
			}
		});

		// Refresh item quantities when connection to server is restored
		this.eventBus.on("server-online", async () => {
			if (this.items && this.items.length > 0) {
				await this.update_items_details(this.items);
			}
		});

		// Setup auto-refresh for item quantities
		// Trigger an immediate refresh once items are available
		this.update_cur_items_details();
		this.refresh_interval = setInterval(() => {
			if (this.filtered_items && this.filtered_items.length > 0) {
				this.update_cur_items_details();
			}
		}, 30000); // Refresh every 30 seconds after the initial fetch

		// Add new event listener for currency changes
		this.eventBus.on("update_currency", (data) => {
			this.selected_currency = data.currency;
			this.exchange_rate = data.exchange_rate;

			// Refresh visible item prices when currency changes
			this.applyCurrencyConversionToItems();
			this.update_cur_items_details();
		});
	},

	async mounted() {
		const profile = await ensurePosProfile();
		if (!this.pos_profile || Object.keys(this.pos_profile).length === 0) {
			this.pos_profile = profile || {};
		}
		
		// Apply correct page limit based on local storage option
		// For non-local storage mode, use smaller initial load to prevent hanging
		const isNonLocalStorageMode = !this.pos_profile.posa_local_storage;
		this.itemsPageLimit = isNonLocalStorageMode ? 500 : this.maxLocalStorageItems;
		
		console.log("ItemsSelector mounted with mode:", {
			local_storage: this.pos_profile.posa_local_storage,
			page_limit: this.itemsPageLimit,
			non_local_storage_mode: isNonLocalStorageMode
		});
		
		// Add loading protection flag
		this.initialLoadInProgress = true;
		
		try {
			if (isNonLocalStorageMode && !this.items_loaded) {
				// For non-local storage mode, clear cache and force controlled load
				console.log("Non-local storage mode: clearing cache and loading items");
				await forceClearAllCache();
				await this.get_items(true);
			} else if (!this.items_loaded) {
				// For local storage mode, check if we have items first
				console.log("Local storage mode: checking for existing items");
				if (!this.items || this.items.length === 0) {
					await this.get_items(false); // Try cache first
				}
			}
		} catch (error) {
			console.error("Error during initial item load:", error);
			// Show user-friendly error
			frappe.show_alert({
				message: __("Failed to load items. Please refresh the page or check your connection."),
				indicator: "red"
			}, 5);
		} finally {
			this.initialLoadInProgress = false;
		}
		
		// Add retry logic if items didn't load
		setTimeout(() => {
			if (!this.items_loaded || !this.items || this.items.length === 0) {
				console.log("Items not loaded after mount, retrying...");
				frappe.show_alert({
					message: __("Items not loaded, retrying..."),
					indicator: "orange"
				}, 3);
				this.get_items(true);
			}
		}, 5000); // Retry after 5 seconds
		
		this.scan_barcoud();
		// Apply the configured items per page on mount
		this.itemsPerPage = this.items_per_page;
		
		// Additional check for items loading after a delay
		setTimeout(() => {
			if (!this.items || this.items.length === 0) {
				console.warn("No items loaded after 10 seconds. Check network or configuration.");
				frappe.show_alert({
					message: __("Items taking time to load. Try clicking 'Reload Items' if needed."),
					indicator: "yellow"
				}, 5);
			}
		}, 10000); // Check after 10 seconds
		
		// Expose debug method to window for easy console access
		window.debugItemsState = () => this.debugItemsState();
		window.testItemsLoad = () => this.testItemsLoad();
		window.ensureItemsVisible = () => this.ensureItemsVisible();
		console.log("ItemsSelector mounted. Debug with: window.debugItemsState()");
		console.log("Test items loading with: window.testItemsLoad()");
		console.log("Ensure items visible with: window.ensureItemsVisible()");
	},

	beforeUnmount() {
		// Clear interval when component is destroyed
		if (this.refresh_interval) {
			clearInterval(this.refresh_interval);
		}

		if (this.itemDetailsRetryTimeout) {
			clearTimeout(this.itemDetailsRetryTimeout);
		}
		this.itemDetailsRetryCount = 0;

		// Call cleanup function for abort controller
		if (this.cleanupBeforeDestroy) {
			this.cleanupBeforeDestroy();
		}

		// Detach scanner if it was attached
		if (document._scannerAttached) {
			try {
				onScan.detachFrom(document);
				document._scannerAttached = false;
			} catch (error) {
				console.warn("Scanner detach error:", error.message);
			}
		}

		if (this.itemWorker) {
			this.itemWorker.terminate();
		}

		this.eventBus.off("update_currency");
		this.eventBus.off("server-online");
		this.eventBus.off("register_pos_profile");
		this.eventBus.off("update_cur_items_details");
		this.eventBus.off("update_offers_counters");
		this.eventBus.off("update_coupons_counters");
		this.eventBus.off("update_customer_price_list");
		this.eventBus.off("update_customer");
		this.eventBus.off("force_reload_items");
	},
};
</script>

<style scoped>
.dynamic-card {
	composes: pos-card;
}

.dynamic-padding {
	/* Equal spacing on all sides for consistent alignment */
	padding: var(--dynamic-sm);
}

.dynamic-scroll {
	transition: max-height var(--transition-normal);
	padding-bottom: var(--dynamic-xs);
	overflow-y: auto;
	scrollbar-gutter: stable;
}

.items-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--dynamic-sm);
	align-items: start;
	align-content: start;
}

.dynamic-item-card {
	margin: var(--dynamic-xs);
	transition: var(--transition-normal);
	background-color: var(--surface-secondary);
	display: flex;
	flex-direction: column;
	height: auto;
	box-sizing: border-box;
}

.dynamic-item-card .v-img {
	object-fit: contain;
}

.dynamic-item-card:hover {
	transform: scale(calc(1 + 0.02 * var(--font-scale)));
}

.text-success {
	color: #4caf50 !important;
}

.sleek-data-table {
	composes: pos-table;
	margin: var(--dynamic-xs);
}

.sleek-data-table:hover {
	box-shadow: var(--shadow-md) !important;
}

.settings-container {
	display: flex;
	align-items: center;
}

.truncate {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* Light mode card backgrounds */
.selection,
.cards {
	background-color: var(--surface-secondary) !important;
}

/* Consistent spacing with navbar and system */
.dynamic-spacing-sm {
	padding: var(--dynamic-sm) !important;
}

.action-btn-consistent {
	margin-top: var(--dynamic-xs) !important;
	padding: var(--dynamic-xs) var(--dynamic-sm) !important;
	transition: var(--transition-normal) !important;
}

.action-btn-consistent:hover {
	background-color: rgba(25, 118, 210, 0.1) !important;
	transform: translateY(-1px) !important;
}

/* Ensure consistent spacing with navbar pattern */
.cards {
	margin-top: var(--dynamic-sm) !important;
	padding: var(--dynamic-sm) !important;
}

/* Responsive breakpoints */
@media (max-width: 768px) {
	.dynamic-padding {
		/* Reduce spacing uniformly on smaller screens */
		padding: var(--dynamic-xs);
	}

	.dynamic-spacing-sm {
		padding: var(--dynamic-xs) !important;
	}

	.action-btn-consistent {
		padding: var(--dynamic-xs) !important;
		font-size: 0.875rem !important;
	}
}

@media (max-width: 480px) {
	.dynamic-padding {
		padding: var(--dynamic-xs);
	}

	.cards {
		padding: var(--dynamic-xs) !important;
	}
}
</style>

import { m as a, p as c } from "./posawesome.bundle-DigdAeK6.mjs";
import { M as g, a as h, c as m, N as C, aA as S, aB as d, ax as p, Y as O, af as I, a4 as y, a9 as v, w as k, ap as P, f as L, d as T, a5 as _, aa as x, $ as M, O as A, at as B, P as D, az as E, ar as U, aw as Q, am as F, ao as b, h as G, n as R, ak as W, k as q, C as z, W as H, Z as J, ae as N, a3 as j, a8 as w, x as X, u as K, a6 as V, ab as Y, q as Z, g as $, D as ee, z as ae, aC as se, b as te, i as ce, R as oe, Q as ne, F as re, a1 as ie, S as le, e as fe, J as ue, I as ge, L as he, K as me, ay as Ce, aq as Se, av as de, aj as pe, s as Oe, as as Ie, al as ye, ac as ve, a2 as ke, a7 as Pe, an as Le, aD as Te, au as _e, j as xe, o as Me, l as Ae, B as Be, _ as De, G as Ee, y as Ue, v as Qe, r as Fe, T as be, E as Ge, A as Re, ah as We, ag as qe, ai as ze, t as He, H as Je, V as Ne, X as je, a0 as we, ad as Xe, U as Ke } from "./posawesome.bundle-DigdAeK6.mjs";
function r(s, e) {
  try {
    const t = a.coupons_cache || {}, o = typeof structuredClone == "function" ? structuredClone(e) : JSON.parse(JSON.stringify(e));
    t[s] = o, a.coupons_cache = t, c("coupons_cache", a.coupons_cache);
  } catch (t) {
    console.error("Failed to cache coupons", t);
  }
}
function i(s) {
  try {
    return (a.coupons_cache || {})[s] || [];
  } catch (e) {
    return console.error("Failed to get cached coupons", e), [];
  }
}
function l(s) {
  try {
    const e = a.coupons_cache || {};
    if (s)
      delete e[s];
    else
      for (const t in e)
        delete e[t];
    a.coupons_cache = e, c("coupons_cache", a.coupons_cache);
  } catch (e) {
    console.error("Failed to clear coupons cache", e);
  }
}
export {
  g as MAX_QUEUE_ITEMS,
  h as addToPersistQueue,
  m as checkDbHealth,
  C as clearAllCache,
  l as clearCoupons,
  S as clearCustomerBalanceCache,
  d as clearExpiredCustomerBalances,
  p as clearItemGroups,
  O as clearLocalStockCache,
  I as clearOfflineCustomers,
  y as clearOfflineInvoices,
  v as clearOfflinePayments,
  k as clearOpeningStorage,
  P as clearPriceListCache,
  L as clearStoredItems,
  T as db,
  _ as deleteOfflineInvoice,
  x as deleteOfflinePayment,
  M as fetchItemStockQuantities,
  A as forceClearAllCache,
  B as getAllStoredItems,
  D as getCacheUsageEstimate,
  i as getCachedCoupons,
  E as getCachedCustomerBalance,
  U as getCachedItemDetails,
  Q as getCachedItemGroups,
  F as getCachedOffers,
  b as getCachedPriceListItems,
  G as getCustomerStorage,
  R as getCustomersLastSync,
  W as getItemUOMs,
  q as getItemsLastSync,
  z as getLastSyncTotals,
  H as getLocalStock,
  J as getLocalStockCache,
  N as getOfflineCustomers,
  j as getOfflineInvoices,
  w as getOfflinePayments,
  X as getOpeningDialogStorage,
  K as getOpeningStorage,
  V as getPendingOfflineInvoiceCount,
  Y as getPendingOfflinePaymentCount,
  Z as getSalesPersonsStorage,
  $ as getStoredItems,
  ee as getTaxInclusiveSetting,
  ae as getTaxTemplate,
  se as getTranslationsCache,
  te as initPersistWorker,
  ce as initPromise,
  oe as initializeStockCache,
  ne as isCacheReady,
  re as isManualOffline,
  ie as isOffline,
  le as isStockCacheReady,
  a as memory,
  fe as memoryInitPromise,
  c as persist,
  ue as purgeOldQueueEntries,
  ge as queueHealthCheck,
  he as reduceCacheUsage,
  me as resetOfflineState,
  r as saveCoupons,
  Ce as saveCustomerBalance,
  Se as saveItemDetailsCache,
  de as saveItemGroups,
  pe as saveItemUOMs,
  Oe as saveItems,
  Ie as saveItemsBulk,
  ye as saveOffers,
  ve as saveOfflineCustomer,
  ke as saveOfflineInvoice,
  Pe as saveOfflinePayment,
  Le as savePriceListItems,
  Te as saveTranslationsCache,
  _e as searchStoredItems,
  xe as setCustomerStorage,
  Me as setCustomersLastSync,
  Ae as setItemsLastSync,
  Be as setLastSyncTotals,
  De as setLocalStockCache,
  Ee as setManualOffline,
  Ue as setOpeningDialogStorage,
  Qe as setOpeningStorage,
  Fe as setSalesPersonsStorage,
  be as setStockCacheReady,
  Ge as setTaxInclusiveSetting,
  Re as setTaxTemplate,
  We as syncOfflineCustomers,
  qe as syncOfflineInvoices,
  ze as syncOfflinePayments,
  He as terminatePersistWorker,
  Je as toggleManualOffline,
  Ne as updateLocalStock,
  je as updateLocalStockCache,
  we as updateLocalStockWithActualQuantities,
  Xe as updateOfflineInvoicesCustomer,
  Ke as validateStockForOfflineInvoice
};

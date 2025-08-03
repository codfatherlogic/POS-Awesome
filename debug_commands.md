# Debug Commands for POS Awesome Item Issues

Please run these commands in your browser console while on the POS page to help diagnose the issue:

## 1. Check Current State
```javascript
// Run this to see the current state of items
window.debugItemsState();
```

## 2. Test Items Loading
```javascript
// This will test the item loading functionality
window.testItemsLoad();
```

## 3. Force Items Reload
```javascript
// This will force a complete reload of items
window.ensureItemsVisible();
```

## 4. Check Vue Component State
```javascript
// Check if the ItemsSelector component is available
console.log("ItemsSelector component:", window.vm?.$refs?.itemsSelector);

// If available, check its state
if (window.vm?.$refs?.itemsSelector) {
    const selector = window.vm.$refs.itemsSelector;
    console.log("Selector state:", {
        items_loaded: selector.items_loaded,
        items_count: selector.items?.length || 0,
        filtered_items_count: selector.filtered_items?.length || 0,
        search: selector.first_search,
        loading: selector.loading
    });
}
```

## 5. Manual Item Reload
```javascript
// Force reload items manually
if (window.vm?.$refs?.itemsSelector) {
    window.vm.$refs.itemsSelector.reload_items_force();
}
```

## 6. Check Network Requests
Open Network tab in DevTools and look for:
- Requests to `/api/method/posawesome.posawesome.api.items.get_items`
- Check if they return data or errors
- Note response times and any failed requests

## Instructions:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Run each command above one by one
4. Copy the output for each command
5. Also describe what you see happening in the UI when you:
   - Search for an item
   - Clear the search
   - Add an item to cart
   - Try to reload items

Please share the console output and describe the exact behavior you're seeing.

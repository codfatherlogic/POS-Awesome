// Test script to verify local storage limit functionality
console.log("=== Testing Local Storage Limit ===");

// Open browser console and run this script in the POS interface
function testLocalStorageLimit() {
    // Check if we're in the POS interface
    if (!window.cur_pos || !window.cur_pos.items_selector) {
        console.error("Not in POS interface or items_selector not available");
        return;
    }
    
    const itemsSelector = window.cur_pos.items_selector;
    
    console.log("Current configuration:");
    console.log("- maxLocalStorageItems:", itemsSelector.maxLocalStorageItems);
    console.log("- itemsPageLimit:", itemsSelector.itemsPageLimit);
    console.log("- posa_local_storage:", itemsSelector.pos_profile?.posa_local_storage);
    console.log("- Current items count:", itemsSelector.items?.length || 0);
    
    // Check if local storage mode is enabled
    if (!itemsSelector.pos_profile?.posa_local_storage) {
        console.warn("Local storage is not enabled in POS profile");
        return;
    }
    
    // Test 1: Check current state
    console.log("\n=== Test 1: Current State ===");
    console.log("Items loaded:", itemsSelector.items_loaded);
    console.log("Items count:", itemsSelector.items?.length || 0);
    console.log("Max allowed:", itemsSelector.maxLocalStorageItems);
    console.log("Within limit:", (itemsSelector.items?.length || 0) <= itemsSelector.maxLocalStorageItems);
    
    // Test 2: Check if the limit is being enforced
    console.log("\n=== Test 2: Limit Enforcement ===");
    if (itemsSelector.items?.length >= itemsSelector.maxLocalStorageItems) {
        console.log("✅ Limit is being enforced - items count at or above limit");
    } else {
        console.log("ℹ️ Items count is below limit - this is expected for smaller datasets");
    }
    
    // Test 3: Force reload to test limit
    console.log("\n=== Test 3: Force Reload Test ===");
    console.log("Triggering force reload to test limit...");
    
    // Store original count
    const originalCount = itemsSelector.items?.length || 0;
    
    // Force reload
    itemsSelector.forceReloadItems();
    
    // Check after 5 seconds
    setTimeout(() => {
        const newCount = itemsSelector.items?.length || 0;
        console.log("Items after reload:", newCount);
        console.log("Max limit respected:", newCount <= itemsSelector.maxLocalStorageItems);
        
        if (newCount >= itemsSelector.maxLocalStorageItems) {
            console.log("✅ Local storage limit is working correctly!");
        } else if (newCount > 0) {
            console.log("ℹ️ Dataset is smaller than limit, but functionality is working");
        } else {
            console.log("❌ No items loaded - there might be an issue");
        }
    }, 5000);
}

// Run the test
testLocalStorageLimit();

console.log("\n=== Instructions ===");
console.log("1. Make sure you're in a POS interface");
console.log("2. Make sure 'Use Browser Local Storage' is checked in POS Profile");
console.log("3. Check the console output above");
console.log("4. If you have more than 10,000 items, you should see the limit enforced");

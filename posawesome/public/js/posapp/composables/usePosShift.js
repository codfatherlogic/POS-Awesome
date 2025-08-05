import { ref, getCurrentInstance } from "vue";
import {
    initPromise,
    checkDbHealth,
    getOpeningStorage,
    setOpeningStorage,
    clearOpeningStorage,
    setTaxTemplate,
} from "../../offline/index.js";

export function usePosShift(openDialog) {
    const { proxy } = getCurrentInstance();
    const eventBus = proxy?.eventBus;

    const pos_profile = ref(null);
    const pos_opening_shift = ref(null);

    async function check_opening_entry() {
        await initPromise;
        await checkDbHealth();
        
        console.log("🏪 Checking POS opening entry...");
        
        // First try to load from cache
        const cachedData = getOpeningStorage();
        if (cachedData && cachedData.pos_profile) {
            console.log("✅ Loading POS Profile from cache:", cachedData.pos_profile.name);
            pos_profile.value = cachedData.pos_profile;
            pos_opening_shift.value = cachedData.pos_opening_shift;
            eventBus?.emit("register_pos_profile", cachedData);
            eventBus?.emit("set_company", cachedData.company);
            try {
                frappe.realtime.emit("pos_profile_registered");
            } catch (e) {
                console.warn("Realtime emit failed", e);
            }
            console.info("LoadPosProfile (cached)");
            return;
        }
        
        // Try API call with timeout and retry logic
        let attempts = 0;
        const maxAttempts = 3;
        
        while (attempts < maxAttempts) {
            attempts++;
            try {
                console.log(`🔄 Attempt ${attempts}/${maxAttempts} to load POS Profile from server...`);
                
                const result = await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('API timeout'));
                    }, 15000); // 15 second timeout
                    
                    frappe.call("posawesome.posawesome.api.shifts.check_opening_shift", {
                        user: frappe.session.user,
                    }).then((r) => {
                        clearTimeout(timeout);
                        resolve(r);
                    }).catch((error) => {
                        clearTimeout(timeout);
                        reject(error);
                    });
                });
                
                if (result.message) {
                    console.log("✅ POS Profile loaded from server:", result.message.pos_profile?.name);
                    pos_profile.value = result.message.pos_profile;
                    pos_opening_shift.value = result.message.pos_opening_shift;
                    if (pos_profile.value.taxes_and_charges) {
                        frappe.call({
                            method: "frappe.client.get",
                            args: {
                                doctype: "Sales Taxes and Charges Template",
                                name: pos_profile.value.taxes_and_charges,
                            },
                            callback: (res) => {
                                if (res.message) {
                                    setTaxTemplate(
                                        pos_profile.value.taxes_and_charges,
                                        res.message,
                                    );
                                }
                            },
                        });
                    }
                    eventBus?.emit("register_pos_profile", result.message);
                    eventBus?.emit("set_company", result.message.company);
                    try {
                        frappe.realtime.emit("pos_profile_registered");
                    } catch (e) {
                        console.warn("Realtime emit failed", e);
                    }
                    console.info("LoadPosProfile");
                    try {
                        setOpeningStorage(result.message);
                    } catch (e) {
                        console.error("Failed to cache opening data", e);
                    }
                    return; // Success, exit function
                } else {
                    console.log("📋 No POS opening shift found, will show opening dialog");
                    openDialog && openDialog();
                    return; // No opening shift, exit function
                }
                
            } catch (error) {
                console.error(`❌ Attempt ${attempts} failed:`, error);
                
                if (attempts >= maxAttempts) {
                    // Final attempt failed, try cache one more time or show dialog
                    console.log("🔄 All attempts failed, trying cache again...");
                    const data = getOpeningStorage();
                    if (data && data.pos_profile) {
                        console.log("✅ Using cached POS Profile as fallback:", data.pos_profile.name);
                        pos_profile.value = data.pos_profile;
                        pos_opening_shift.value = data.pos_opening_shift;
                        eventBus?.emit("register_pos_profile", data);
                        eventBus?.emit("set_company", data.company);
                        try {
                            frappe.realtime.emit("pos_profile_registered");
                        } catch (e) {
                            console.warn("Realtime emit failed", e);
                        }
                        console.info("LoadPosProfile (cached fallback)");
                        return;
                    }
                    console.log("📋 No cache available, showing opening dialog");
                    openDialog && openDialog();
                    return;
                } else {
                    // Wait before retry
                    console.log(`⏳ Waiting 2 seconds before retry...`);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
            }
        }
    }

    function get_closing_data() {
        return frappe
            .call(
                "posawesome.posawesome.doctype.pos_closing_shift.pos_closing_shift.make_closing_shift_from_opening",
                { opening_shift: pos_opening_shift.value },
            )
            .then((r) => {
                if (r.message) {
                    eventBus?.emit("open_ClosingDialog", r.message);
                }
            });
    }

    function submit_closing_pos(data) {
        frappe
            .call(
                "posawesome.posawesome.doctype.pos_closing_shift.pos_closing_shift.submit_closing_shift",
                { closing_shift: data },
            )
            .then((r) => {
                if (r.message) {
                    pos_opening_shift.value = null;
                    pos_profile.value = null;
                    clearOpeningStorage();
                    eventBus?.emit("show_message", {
                        title: `POS Shift Closed`,
                        color: "success",
                    });
                    check_opening_entry();
                }
            });
    }

    return { pos_profile, pos_opening_shift, check_opening_entry, get_closing_data, submit_closing_pos };
}

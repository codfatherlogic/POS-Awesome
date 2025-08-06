import { ref, onUnmounted } from "vue";

export function useDatabaseStats(pollInterval = 10000, windowSize = 60) {
    const dbStats = ref(null);
    const history = ref([]);
    const loading = ref(true);
    const error = ref(null);
    let timer = null;
    let retryCount = 0;
    const maxRetries = 3;

    async function fetchDatabaseStats() {
        loading.value = true;
        error.value = null;
        try {
            const res = await frappe.call({
                method: "posawesome.posawesome.api.utilities.get_database_usage",
            });
            if (res && res.message) {
                dbStats.value = res.message;
                history.value.push(res.message);
                if (history.value.length > windowSize) history.value.shift();
                retryCount = 0; // Reset retry count on success
            } else {
                error.value = "No data from server";
            }
        } catch (e) {
            retryCount++;
            console.warn(`Database stats fetch failed (attempt ${retryCount}/${maxRetries}):`, e.message || e);
            
            // Stop retrying after max attempts to prevent resource exhaustion
            if (retryCount >= maxRetries) {
                console.warn("Max retry attempts reached for database stats. Stopping further requests.");
                error.value = "Database stats temporarily unavailable";
                if (timer) {
                    clearInterval(timer);
                    timer = null;
                }
                return;
            }
            
            error.value = e.message || e;
        } finally {
            loading.value = false;
        }
    }

    // Only start fetching if user is properly authenticated
    if (frappe.session?.user && frappe.session.user !== 'Guest') {
        fetchDatabaseStats();
        timer = window.setInterval(fetchDatabaseStats, pollInterval);
    } else {
        console.warn("User not authenticated, skipping database stats");
        loading.value = false;
        error.value = "Authentication required";
    }

    onUnmounted(() => {
        if (timer) clearInterval(timer);
    });

    return { dbStats, history, loading, error };
} 
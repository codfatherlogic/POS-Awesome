import { ref, onUnmounted } from "vue";

export function useServerStats(pollInterval = 10000, windowSize = 60) {
    const cpu = ref(null);
    const memory = ref(null);
    const memoryTotal = ref(null);
    const memoryUsed = ref(null);
    const memoryAvailable = ref(null);
    const history = ref([]);
    const loading = ref(true);
    const error = ref(null);
    let timer = null;
    let retryCount = 0;
    const maxRetries = 3;

    async function fetchServerStats() {
        loading.value = true;
        error.value = null;
        try {
            const res = await frappe.call({
                method: "posawesome.posawesome.api.utilities.get_server_usage",
            });
            if (res && res.message) {
                cpu.value = res.message.cpu_percent;
                memory.value = res.message.memory_percent;
                memoryTotal.value = res.message.memory_total;
                memoryUsed.value = res.message.memory_used;
                memoryAvailable.value = res.message.memory_available;
                const uptime = res.message.uptime;
                history.value.push({
                    cpu: cpu.value,
                    memory: memory.value,
                    memoryTotal: memoryTotal.value,
                    memoryUsed: memoryUsed.value,
                    memoryAvailable: memoryAvailable.value,
                    uptime: uptime
                });
                if (history.value.length > windowSize) history.value.shift();
                retryCount = 0; // Reset retry count on success
            } else {
                error.value = "No data from server";
            }
        } catch (e) {
            retryCount++;
            console.warn(`Server stats fetch failed (attempt ${retryCount}/${maxRetries}):`, e.message || e);
            
            // Stop retrying after max attempts to prevent resource exhaustion
            if (retryCount >= maxRetries) {
                console.warn("Max retry attempts reached for server stats. Stopping further requests.");
                error.value = "Server stats temporarily unavailable";
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
        fetchServerStats();
        timer = window.setInterval(fetchServerStats, pollInterval);
    } else {
        console.warn("User not authenticated, skipping server stats");
        loading.value = false;
        error.value = "Authentication required";
    }

    onUnmounted(() => {
        if (timer) clearInterval(timer);
    });

    return { cpu, memory, memoryTotal, memoryUsed, memoryAvailable, history, loading, error };
} 
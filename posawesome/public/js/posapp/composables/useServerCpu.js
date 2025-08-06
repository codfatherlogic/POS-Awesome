import { ref, onUnmounted } from "vue";

const API_URL = "/api/method/posawesome.posawesome.api.utilities.get_server_usage";

export function useServerCpu(pollInterval = 10000, windowSize = 60) {
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

    async function fetchServerCpu() {
        loading.value = true;
        error.value = null;
        try {
            const res = await fetch(API_URL);
            const data = await res.json();
            if (data && data.message) {
                cpu.value = data.message.cpu_percent;
                memory.value = data.message.memory_percent;
                memoryTotal.value = data.message.memory_total;
                memoryUsed.value = data.message.memory_used;
                memoryAvailable.value = data.message.memory_available;
                const uptime = data.message.uptime;
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
            console.warn(`Server CPU stats fetch failed (attempt ${retryCount}/${maxRetries}):`, e.message || e);
            
            // Stop retrying after max attempts to prevent resource exhaustion
            if (retryCount >= maxRetries) {
                console.warn("Max retry attempts reached for server CPU stats. Stopping further requests.");
                error.value = "Server CPU stats temporarily unavailable";
                if (timer) {
                    clearInterval(timer);
                    timer = null;
                }
                return;
            }
            
            error.value = e.message;
        } finally {
            loading.value = false;
        }
    }

    // Only start fetching if user is properly authenticated
    if (frappe.session?.user && frappe.session.user !== 'Guest') {
        fetchServerCpu();
        timer = window.setInterval(fetchServerCpu, pollInterval);
    } else {
        console.warn("User not authenticated, skipping server CPU stats");
        loading.value = false;
        error.value = "Authentication required";
    }

    onUnmounted(() => {
        if (timer) clearInterval(timer);
    });

    return { cpu, memory, memoryTotal, memoryUsed, memoryAvailable, history, loading, error };
} 
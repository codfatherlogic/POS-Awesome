import { getOpeningStorage } from "../offline/index.js";

// Global rate limiting to prevent infinite API calls
let lastCallTime = 0;
let inProgress = false;
let cachedResult = null;
let consecutiveFailures = 0;
const RATE_LIMIT_MS = 5000; // Increased to 5 seconds between API calls
const MAX_CONSECUTIVE_FAILURES = 3;
const FAILURE_TIMEOUT = 30000; // 30 seconds timeout after max failures

export async function ensurePosProfile() {
	const now = Date.now();
	
	// Circuit breaker: if too many consecutive failures, wait longer
	if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
		if (lastCallTime && (now - lastCallTime) < FAILURE_TIMEOUT) {
			console.log("🚫 ensurePosProfile: Circuit breaker open due to consecutive failures, waiting...");
			return cachedResult;
		} else {
			console.log("⚡ ensurePosProfile: Circuit breaker reset, attempting call");
			consecutiveFailures = 0; // Reset after timeout
		}
	}
	
	// If already in progress, wait for the existing call
	if (inProgress) {
		console.log("🔄 ensurePosProfile: Call already in progress, waiting...");
		return new Promise((resolve) => {
			let attempts = 0;
			const maxAttempts = 50; // Max 5 seconds wait
			const checkComplete = () => {
				attempts++;
				if (!inProgress || attempts >= maxAttempts) {
					resolve(cachedResult);
				} else {
					setTimeout(checkComplete, 100);
				}
			};
			checkComplete();
		});
	}
	
	// Rate limiting - prevent too frequent calls
	if (lastCallTime && (now - lastCallTime) < RATE_LIMIT_MS) {
		console.log("🚫 ensurePosProfile: Rate limited, returning cached result");
		return cachedResult;
	}
	
	console.log("🔄 ensurePosProfile: Starting POS Profile check");
	inProgress = true;
	lastCallTime = now;
	
	try {
		// First check if we already have a valid profile in frappe.boot
		const bootProfile = frappe?.boot?.pos_profile;
		if (bootProfile && bootProfile.warehouse && bootProfile.selling_price_list) {
			console.log("✅ ensurePosProfile: Found valid boot profile:", bootProfile.name);
			cachedResult = bootProfile;
			consecutiveFailures = 0; // Reset failure count on success
			inProgress = false;
			return bootProfile;
		}
		
		// Try to fetch from server with timeout
		try {
			console.log("🌐 ensurePosProfile: Fetching from server...");
			const res = await Promise.race([
				frappe.call({
					method: "posawesome.posawesome.api.utils.get_active_pos_profile",
					args: { user: frappe.session.user },
				}),
				new Promise((_, reject) => 
					setTimeout(() => reject(new Error("POS Profile API timeout")), 8000)
				)
			]);
			
			if (res.message) {
				console.log("✅ ensurePosProfile: Got profile from server:", res.message.name);
				frappe.boot.pos_profile = res.message;
				cachedResult = res.message;
				consecutiveFailures = 0; // Reset failure count on success
				inProgress = false;
				return res.message;
			}
		} catch (e) {
			console.error("❌ ensurePosProfile: Failed to fetch active POS profile", e);
			consecutiveFailures++;
		}
		
		// Try cached data
		try {
			const cached = getOpeningStorage();
			if (cached && cached.pos_profile) {
				console.log("📦 ensurePosProfile: Using cached profile:", cached.pos_profile.name);
				cachedResult = cached.pos_profile;
				consecutiveFailures = 0; // Reset failure count on success
				inProgress = false;
				return cached.pos_profile;
			}
		} catch (e) {
			console.error("❌ ensurePosProfile: Failed to get cached profile", e);
			consecutiveFailures++;
		}
		
		// Fallback to boot profile even if incomplete
		if (bootProfile) {
			console.log("⚠️ ensurePosProfile: Using incomplete boot profile:", bootProfile.name || 'unnamed');
			cachedResult = bootProfile;
			inProgress = false;
			return bootProfile;
		}
		
		console.error("❌ ensurePosProfile: No POS Profile found anywhere");
		consecutiveFailures++;
		cachedResult = null;
		inProgress = false;
		return null;
	} catch (error) {
		console.error("❌ ensurePosProfile: Unexpected error:", error);
		consecutiveFailures++;
		inProgress = false;
		return cachedResult;
	}
}

import frappe

# Initialize the database
frappe.init(site="pos")
frappe.connect()

# Check users
users = frappe.get_all('User', filters={'enabled': 1}, fields=['name', 'email', 'first_name'])
print("Enabled users:")
for user in users:
    print(f"  - {user.name} ({user.email}) - {user.first_name}")

# Check POS Profiles
pos_profiles = frappe.get_all('POS Profile', fields=['name', 'user', 'company', 'disabled'])
print(f"\nPOS Profiles ({len(pos_profiles)}):")
for profile in pos_profiles:
    print(f"  - {profile.name}: user={profile.user}, company={profile.company}, disabled={profile.disabled}")

# Check if we can call the function directly
try:
    sys_path = frappe.get_module_path("posawesome", "posawesome", "api", "utils")
    print(f"\nModule path: {sys_path}")
    
    from posawesome.posawesome.api.utils import get_active_pos_profile
    
    # Try with different users
    for user in users[:3]:  # Test with first 3 users
        try:
            frappe.set_user(user.name)
            active_profile = get_active_pos_profile()
            print(f"\nActive POS Profile for {user.name}: {active_profile}")
        except Exception as e:
            print(f"\nError getting profile for {user.name}: {e}")
            
except Exception as e:
    print(f"\nError importing or calling function: {e}")

frappe.destroy()

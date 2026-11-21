from getpass import getpass

from auth import create_user_account


email = input("Admin email: ").strip()
name = input("Admin display name: ").strip()
password = getpass("Admin password (minimum 8 characters): ")
confirmation = getpass("Confirm password: ")
if password != confirmation:
    raise SystemExit("Passwords do not match.")

try:
    account_id = create_user_account(email, name, password, role="admin")
except ValueError as error:
    raise SystemExit(str(error)) from error
print(f"Admin account created. EduAI ID: {account_id}")

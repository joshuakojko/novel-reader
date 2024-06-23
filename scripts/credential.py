import keyring
import getpass

# Run python cred.py to store GOOGLE_CLIENT_SECRET in (service_name="oauth", username=GOOGLE_CLIENT_ID, password=GOOGLE_CLIENT_SECRET)

def save_password(service_name, username):
    password = getpass.getpass(f"Enter password for {username}: ")
    keyring.set_password(service_name, username, password)
    print(f"Password for {username} saved to the keyring.")

if __name__ == "__main__":
    service_name = input("Enter your service name: ")
    username = input("Enter your username: ")
    save_password(service_name, username)
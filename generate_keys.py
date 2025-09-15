# generate_keys.py (Compatible with very old versions)
import streamlit_authenticator as stauth

# 1. Enter the passwords you want to hash here
passwords_to_hash = ["abc", "def"] 

# 2. Create an instance of the Hasher
hasher = stauth.Hasher()

# 3. Loop through passwords and hash them one by one
hashed_passwords = []
for password in passwords_to_hash:
    hashed_password = hasher.hash(password)
    hashed_passwords.append(hashed_password)

# 4. Print the final list of hashed passwords
print(hashed_passwords)
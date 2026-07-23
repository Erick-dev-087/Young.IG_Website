import secrets

def generate_secret_key(length=32):
    return secrets.token_hex(length)

if __name__ == "__main__":
    print("="*70)
    print("Copy the following values into the .env file:")
    print(f"APP_SECRET = {generate_secret_key(32)}")
    print(f"JWT_SECRET = {generate_secret_key(32)}")
    print(f"JWT_REFRESH_SECRET = {generate_secret_key(32)}")
    print(f"PASSWORD_RESET_SALT = {generate_secret_key(32)}")
    print("="*70)  
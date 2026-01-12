import bcrypt

password = "Admin@123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print("Hashed password:", hashed.decode('utf-8'))
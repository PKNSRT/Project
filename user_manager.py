import json
from werkzeug.security import generate_password_hash, check_password_hash

class UserManager:
    def __init__(self, json_file='users.json'):
        self.json_file = json_file
        self.users = self.load_users()

    def load_users(self):
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                # ตรวจสอบรหัสผ่านที่ยังไม่ได้เข้ารหัส
                for username, data in users.items():
                    if not str(data['password']).startswith('pbkdf2:'):
                        users[username]['password'] = str(data['password'])
                return users
        except FileNotFoundError:
            # สร้างไฟล์ใหม่พร้อม admin user
            default_users = {
                "admin": {
                    "password": "s",
                    "is_admin": True
                }
            }
            self.save_users(default_users)
            return default_users

    def save_users(self, users=None):
        if users is None:
            users = self.users
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)

    def verify_user(self, username, password):
        if username in self.users:
            return self.users[username]['password'] == password
        return False

    def add_user(self, username, password, is_admin=False):
        if username in self.users:
            return False
        self.users[username] = {
            "password": password,
            "is_admin": is_admin
        }
        self.save_users()
        return True

    def update_user(self, username, new_username=None, new_password=None):
        if username not in self.users:
            return False
        
        user_data = self.users[username].copy()
        
        if new_password:
            user_data['password'] = new_password
            
        if new_username and new_username != username:
            if new_username in self.users:
                return False
            self.users[new_username] = user_data
            del self.users[username]
        else:
            self.users[username] = user_data
            
        self.save_users()
        return True

    def delete_user(self, username):
        if username in self.users and not self.users[username]['is_admin']:
            del self.users[username]
            self.save_users()
            return True
        return False

    def is_admin(self, username):
        return username in self.users and self.users[username]['is_admin']

    def get_users(self):
        return {username: {
            'username': username,
            'password': data['password'],
            'is_admin': data['is_admin']
        } for username, data in self.users.items()}
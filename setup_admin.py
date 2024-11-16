import traceback
from werkzeug.security import generate_password_hash
from connect import get_db_connection
from mysql.connector import Error

def setup_admin(username, password):
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (username, hashed_password) )
            conn.commit()
            cur.close()
            print("Admin account created successfully.")
        except Error as e:
            traceback.print_exc()
            print(f"Database error: {e}")
        finally:
            
            conn.close()

if __name__ == "__main__":
    
    # Set up the initial admin account
    setup_admin('edet', 'edet')
    # setup_admin('admin', 'admin1234abcd')
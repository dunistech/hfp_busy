import mysql.connector, os
# Function to establish a direct MySQL connection
def get_db_connection():
    try:
        # Fetching connection parameters from environment variables
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),  # Default is 'localhost'
            database=os.getenv('DB_NAME', 'hfp_db'),  # Default database name
            user=os.getenv('DB_USER', 'root'),  # Default MySQL username
            password=os.getenv('DB_PASSWORD', '')  # Default MySQL password
        )
        if conn.is_connected():
            print("Successfully connected to MySQL database!")
        return conn
    except mysql.connector.Error as e:
        print(f"Error: {e}")
    return None

def fetch_categories():
    conn = get_db_connection()
    categories = []
    if conn:
        try:
            cur = conn.cursor(dictionary=True)  # Fetch rows as dictionaries
            cur.execute("SELECT id, category_name FROM categories")
            result = cur.fetchall()
            # categories = {row['id']: row['category_name'] for row in result}  # Convert to dict

            categories = [{"id": row['id'], 'name': row['category_name'] } for row in result]  # List of named tuples
            
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
        finally:
            cur.close()
            conn.close()
            
    # return categories  # Return categories as dict
    return {"categories": categories}

def fetch_plans():
    conn = get_db_connection()
    plans = []
    if conn:
        try:
            cur = conn.cursor(buffered=True, dictionary=True)  # Fetch rows as dictionaries
            # cur.execute("SELECT id, category_name FROM categories")
             # Fetch subscription plans
            cur.execute("""
                SELECT id, plan_name, amount, duration
                FROM subscription_plans
            """)
            
            # subscription_plans = cur.fetchall()
            
            result = cur.fetchall()
            # categories = {row['id']: row['category_name'] for row in result}  # Convert to dict

            plans = [
                {
                "id": row['id'], 'plan_name': row['plan_name'],
                'amount': row['amount'], 'duration':row['duration']
            } 
            for row in result
            ]  # List of named tuples
            
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
        finally:
            cur.close()
            conn.close()
            
    # return categories  # Return categories as dict
    return {"subscription_plans": plans }

def create_tables():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()

            # Create tables with foreign key constraints
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_registration_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    name VARCHAR(250),
                    phone VARCHAR(250)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    profile_image TEXT,
                    suspended BOOLEAN DEFAULT FALSE,
                    activation_token TEXT,
                    is_activated BOOLEAN DEFAULT FALSE,
                    registration_request_id INT,
                    name VARCHAR(250),
                    phone VARCHAR(250),
                    FOREIGN KEY (registration_request_id) REFERENCES user_registration_requests(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS business_registration_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    business_name VARCHAR(100) NOT NULL,
                    shop_no VARCHAR(100) NOT NULL,
                    phone_number VARCHAR(20),
                    description TEXT NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INT,
                    category VARCHAR(50) NOT NULL,
                    block_num VARCHAR(50),
                    email VARCHAR(100),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    owner_id INT,
                    business_name VARCHAR(100) NOT NULL,
                    shop_no VARCHAR(100) NOT NULL,
                    phone_number VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    is_subscribed BOOLEAN DEFAULT FALSE,
                    media_type ENUM('image', 'video'),
                    media_url TEXT,
                    category VARCHAR(50) NOT NULL,
                    block_num VARCHAR(50),
                    email VARCHAR(100),
                    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS images_videos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    business_id INT,
                    media_type ENUM('image', 'video'),
                    media_url TEXT NOT NULL,
                    FOREIGN KEY (business_id) REFERENCES businesses(id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    category_name VARCHAR(255) UNIQUE NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS business_categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    business_id INT,
                    category_id INT,
                    FOREIGN KEY (business_id) REFERENCES businesses(id),
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    UNIQUE (business_id, category_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    profile_pic VARCHAR(255)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    plan_name VARCHAR(50) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    duration INT NOT NULL,
                    UNIQUE (plan_name, duration)
                );
            """)           
            
            # cur.execute("""INSERT INTO subscription_plans (plan_name, amount, duration) VALUES 
            #             ('Monthly', 10000, 1), 
            #             ('Yearly', 85000, 12)
            #             """)   
            # Define the subscription plans you want to insert
            plans = [
                ('Monthly', 2000, 1),
                ('Yearly', 20000, 12)
            ]

            # Loop through each plan and check if it exists before inserting
            for plan_name, amount, duration in plans:
                # Check if the plan already exists
                cur.execute("SELECT 1 FROM subscription_plans WHERE plan_name = %s", (plan_name,))
                result = cur.fetchone()
                
                # If no result is found, insert the new plan
                if result is None:
                    cur.execute("""INSERT INTO subscription_plans (plan_name, amount, duration) 
                                VALUES (%s, %s, %s)""", (plan_name, amount, duration))
                    print(f"Inserted plan: {plan_name}")
                else:
                    print(f"Plan '{plan_name}' already exists, skipping insertion.")

            # Don't forget to commit the transaction after insertion
            # conn.commit()
 

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    business_id INT,
                    subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('pending', 'confirmed'),
                    plan_id INT,
                    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    subscription_id INT,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    amount DECIMAL(10, 2) NOT NULL,
                    payment_status ENUM('pending', 'completed'),
                    payment_method VARCHAR(50),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS claim_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    business_id INT,
                    user_id INT,
                    phone_number VARCHAR(255),
                    email VARCHAR(255),
                    category VARCHAR(255),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (business_id) REFERENCES businesses(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)

            print("Database tables created successfully")
            conn.commit()

        except mysql.connector.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("Could not open connection to the database")

# Call the function to initialize the database
create_tables()









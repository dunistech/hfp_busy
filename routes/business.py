from random import randint
import traceback
from flask import Blueprint, request, render_template, redirect, session, url_for, flash
import mysql
from utils.helpers import get_db_connection

bp = Blueprint('business', __name__)
       
@bp.route('/businesses')
def businesses():
    
    if 'admin_logged_in' not in session:
        return redirect(url_for('index.home'))

    conn = get_db_connection()

    if conn:
        try:
            cur = conn.cursor(buffered=True, dictionary=True)
            
            # Fetch pending claim requests
            cur.execute(""" SELECT * FROM businesses """)
            businesses = cur.fetchall()
            
            # Count pending user registration requests
            # cur.execute("SELECT COUNT(*) FROM businesses")
            # business_count = cur.fetchone()[0]
            
            context = {
                "businesses":businesses,
                "business_count": len(businesses)
            }
            
            cur.close()
            conn.close()
            
            return render_template('businesses.html', **context )  # Pass count to template

        except Exception as e:
            traceback.print_exc()
            print(f"Database error: {e}")
            flash("Error occurred during dashboard retrieval.", 'error')
            return f"{e}"
        finally:
            conn.close()
            
@bp.route('/admin/review_claim/<int:request_id>', methods=['GET', 'POST'])
def review_claim(request_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))

    print(f"Review Claim function called with request_id: {request_id}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if request.method == 'POST':
            # Fetch the claim request details
            cur.execute("""
                SELECT business_id, user_id, phone_number, email, category, description
                FROM claim_requests
                WHERE id = %s
            """, (request_id,))
            claim_request = cur.fetchone()

            if claim_request:
                business_id, user_id, phone_number, email, category_name, description = claim_request
                print(f"Updating business with ID {business_id} to new owner ID {user_id}")

                # Check if the category already exists
                cur.execute("SELECT id FROM categories WHERE category_name = %s", (category_name,))
                category = cur.fetchone()

                # If the category does not exist, insert it
                if category is None:
                    id = randint(2, 9999)
                    cur.execute("INSERT INTO categories (id, category_name) VALUES (%s, %s)", (id, category_name,) )
                    
                    # category_id = cur.fetchone()[0]
                    category_id = id
                    # category_id = category[0]

                # Update the claim request to mark it as reviewed
                cur.execute("""
                    UPDATE claim_requests
                    SET reviewed = TRUE
                    WHERE id = %s
                """, (request_id,))
                print("Claim request marked as reviewed")

                # Update the businesses table with the new owner and other details from the claim
                cur.execute("""
                    UPDATE businesses
                    SET owner_id = %s,
                        phone_number = %s,
                        email = %s,
                        description = %s,
                        category = %s
                    WHERE id = %s
                """, (user_id, phone_number, email, description, category_name, business_id))
                print("Business ownership, details, and category updated")

                # Link the business with its category
                cur.execute("""
                    INSERT INTO business_categories (business_id, category_id)
                    VALUES (%s, %s)""", (business_id, category_id))
                print("Business linked with category")

                conn.commit()  # Ensure all changes are committed
                flash("Claim request approved and business ownership updated!", 'success')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash("Claim request not found.", 'error')

        # Fetch the claim request details for display
        cur.execute("""
            SELECT cr.id, b.business_name, u.username, cr.phone_number, cr.email, cr.category, cr.description
            FROM claim_requests cr
            JOIN businesses b ON cr.business_id = b.id
            JOIN users u ON cr.user_id = u.id
            WHERE cr.id = %s
        """, (request_id,))
        claim_request = cur.fetchone()
        print(f"Claim Request for Display: {claim_request}")

    except Exception as e:
        flash('Error occurred during claim review.', 'error')
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    return render_template('review_claim.html', claim_request=claim_request)


@bp.route('/process_business_registration', methods=['POST'])
def process_business_registration():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    
    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.form.get('user_id')
    business_name = request.form.get('business_name')
    shop_no = request.form.get('shop_no')
    phone_number = request.form.get('phone_number')
    description = request.form.get('description')
    category_name = request.form.get('category')
    block_num = request.form.get('block_num')
    email = request.form.get('email')  # Get email address

    print(f"Processing business registration with: {user_id}, {business_name}, {shop_no}, {phone_number}, {description}, {category_name}, {block_num}, {email}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Check if the category already exists
        cur.execute("SELECT id FROM categories WHERE category_name = %s", (category_name,))
        category = cur.fetchone()
        
        # If the category does not exist, insert it
        if category is None:
            cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
            conn.commit()  # Commit to generate the ID
            cur.execute("SELECT LAST_INSERT_ID()")
            category_id = cur.fetchone()[0]
            print(f"Inserted new category with ID: {category_id}")
        else:
            category_id = category[0]
            print(f"Found existing category with ID: {category_id}")

        # Insert the new business with the correct owner_id and email
        cur.execute("""
            INSERT INTO businesses (owner_id, business_name, shop_no, phone_number, description, block_num, email, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, business_name, shop_no, phone_number, description, block_num, email, category_name))
        conn.commit()  # Commit to generate the ID
        cur.execute("SELECT LAST_INSERT_ID()")
        business_id = cur.fetchone()[0]
        print(f"Inserted new business with ID: {business_id}")

        # Link the business with its category
        cur.execute("INSERT INTO business_categories (business_id, category_id) VALUES (%s, %s)", (business_id, category_id))
        conn.commit()
        print(f"Linked business ID {business_id} with category ID {category_id}")

        # Update the registration request to mark it as processed
        cur.execute("UPDATE business_registration_requests SET processed = TRUE WHERE business_name = %s", (business_name,))
        conn.commit()
        print(f"Marked business registration '{business_name}' as processed.")

        flash('Business registered successfully and registration request marked as processed.', 'success')
    except mysql.connector.Error as e:
        flash('Error occurred during business registration.', 'error')
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin.admin_dashboard'))


@bp.route('/subscribe/<int:business_id>', methods=['POST'])
def subscribe(business_id):
    
    # if 'user_logged_in' not in session or 'admin_id' not in session:
    if 'admin_id' not in session:
        return redirect(url_for('auth.user_login'))
    
    user_id = session.get('user_id')
    plan_id = request.form.get('plan_id')
    
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Check if the business belongs to the user
            cur.execute("SELECT owner_id FROM businesses WHERE id = %s", (business_id,))
            owner = cur.fetchone()
            
            if owner and owner[0] == user_id or session.get('admin_id'):
                # Insert subscription into the subscriptions table
                cur.execute("""
                    INSERT INTO subscriptions (business_id, plan_id, status) 
                    VALUES (%s, %s, 'confirmed')
                """, (business_id, plan_id))
                
                # Update the business as subscribed
                cur.execute("""
                    UPDATE businesses
                    SET is_subscribed = TRUE
                    WHERE id = %s
                """, (business_id,))
                
                conn.commit()
                flash("Subscription successful!", "success")
            else:
                flash("Unauthorized action.", "error")
            
            cur.close()
        except Exception as e:
            conn.rollback()
            flash(f"Database error: {e}", "error")
        finally:
            conn.close()
    
    return redirect(request.referrer)


@bp.route('/claim_business/<int:business_id>', methods=['GET', 'POST'])
def claim_business(business_id):
    username = session.get('username')
    user_id = session.get('user_id')

    if not username or not user_id:
        flash("You need to be logged in to claim a business.", 'warning')
        return redirect(url_for('index.home'))

    conn = get_db_connection()
    business = None

    try:
        cur = conn.cursor()

        # Fetch the business details
        cur.execute("SELECT * FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()

        if request.method == 'POST':
            # Process the form submission
            phone_number = request.form['phone_number']
            email = request.form['email']
            category = request.form['category']
            description = request.form['description']

            cur.execute("""
                INSERT INTO claim_requests (business_id, user_id, phone_number, email, category, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (business_id, user_id, phone_number, email, category, description))

            conn.commit()
            flash("Claim request submitted successfully! The admin will review your request.", 'success')
            return redirect(url_for('index.home'))

        cur.close()
    except Exception as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()

    return render_template('claim_business.html', business=business)


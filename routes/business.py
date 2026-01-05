from random import randint
import traceback
import os
from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
import mysql
from services.schema import business_schema
from services.seo import build_seo
from utils.helpers import get_db_connection, upload_file
from utils.slug import generate_unique_slug, slugify


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

# 



# UPDATED ON 6/19/2025 AROUND 4:11PM
# UPDATED ON 11/29/2025 - Added second media support
@bp.route('/business/<int:business_id>', methods=['GET', 'POST'])
def business_profile(business_id):
    """Manage individual business profile (admin or owner access only)"""
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    business = None
    subscription_plans = []
    all_categories = []
    business_categories = []
    business_category_ids = []

    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # Get user role
            cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            is_admin = user and user['role'] == 'admin'

            # Get business and check access
            cur.execute("""
                SELECT b.*, 
                       CASE 
                           WHEN b.status = 'active' THEN 'Active'
                           WHEN b.status = 'pending' THEN 'Pending Approval'
                           WHEN b.status = 'suspended' THEN 'Suspended'
                           ELSE b.status
                       END as status_display
                FROM businesses b
                WHERE b.id = %s
            """, (business_id,))
            business = cur.fetchone()

            if not business:
                flash('Business not found.', 'error')
                return redirect(url_for('user.profile'))

            if not is_admin and business['owner_id'] != user_id:
                flash('You do not have permission to access this business.', 'danger')
                return redirect(url_for('user.profile'))

            # Get all available categories
            cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
            all_categories = cur.fetchall()

            # Get business's current categories
            cur.execute("""
                SELECT c.id, c.category_name 
                FROM business_categories bc
                JOIN categories c ON bc.category_id = c.id
                WHERE bc.business_id = %s
            """, (business_id,))
            business_categories = cur.fetchall()
            business_category_ids = [cat['id'] for cat in business_categories]

            # Handle form submission for business updates
            if request.method == 'POST':
                business_name = request.form.get('business_name')
                description = request.form.get('description')
                phone_number = request.form.get('phone_number')
                email = request.form.get('email')
                shop_no = request.form.get('shop_no')
                block_num = request.form.get('block_num')
                address = request.form.get('address')
                facebook = request.form.get('facebook_link')
                instagram = request.form.get('instagram_link')
                twitter = request.form.get('twitter_link')
                website = request.form.get('website_url')
                
                # Primary media
                file = request.files.get('business_media')
                # Secondary media
                file2 = request.files.get('business_media_2')

                update_fields_raw = {
                    'business_name': business_name,
                    'description': description,
                    'phone_number': phone_number,
                    'email': email,
                    'shop_no': shop_no,
                    'block_num': block_num,
                    'address': address,
                    'facebook_link': facebook,
                    'instagram_link': instagram,
                    'twitter_link': twitter,
                    'website_url': website
                }

                # Handle primary media upload
                if file and file.filename:
                    file_path = upload_file(file)
                    if file_path:
                        mimetype = getattr(file, 'mimetype', '') or getattr(file, 'content_type', '')
                        print(f"Uploaded primary file mimetype: {mimetype}")
                        if mimetype and mimetype.startswith('video/'):
                            update_fields_raw['media_url'] = file_path
                            update_fields_raw['media_type'] = 'video'
                        else:
                            update_fields_raw['media_url'] = file_path
                            update_fields_raw['media_type'] = 'image'
                        print(f"Primary file uploaded to: {file_path}")

                # Handle secondary media upload with validation
                if file2 and file2.filename:
                    # Get current media types
                    current_media_type = business.get('media_type', '')
                    if file and file.filename:
                        # If uploading new primary media, use that type
                        current_media_type = 'video' if (getattr(file, 'mimetype', '') or '').startswith('video/') else 'image'
                    
                    # Determine new secondary media type
                    mimetype2 = getattr(file2, 'mimetype', '') or getattr(file2, 'content_type', '')
                    new_media_type_2 = 'video' if mimetype2.startswith('video/') else 'image'
                    
                    # Validation: Don't allow 2 videos
                    if current_media_type == 'video' and new_media_type_2 == 'video':
                        flash('Cannot upload 2 videos. Please upload 1 video + 1 image, or 2 images.', 'error')
                    else:
                        # Delete old secondary media if exists
                        if business.get('media_url_2'):
                            try:
                                old_file_path = business['media_url_2']
                                if old_file_path.startswith('/static/'):
                                    old_file_path = old_file_path[1:]  # Remove leading slash
                                full_path = os.path.join(app.root_path, old_file_path)
                                if os.path.exists(full_path):
                                    os.remove(full_path)
                                    print(f"Deleted old secondary media: {full_path}")
                            except Exception as e:
                                print(f"Error deleting old secondary media: {e}")
                        
                        # Upload new secondary media
                        file_path_2 = upload_file(file2)
                        if file_path_2:
                            update_fields_raw['media_url_2'] = file_path_2
                            update_fields_raw['media_type_2'] = new_media_type_2
                            print(f"Secondary file uploaded to: {file_path_2}")

                selected_category_ids = request.form.getlist('categories')
                    
                # Remove keys with None or empty strings
                update_fields = {k: v for k, v in update_fields_raw.items() if v is not None and v != ''}

                # Only execute update when there are fields to change
                if update_fields:
                    set_clause = ', '.join([f"{k} = %s" for k in update_fields])
                    values = list(update_fields.values())

                    if not is_admin:
                        update_sql = f"UPDATE businesses SET {set_clause} WHERE id = %s AND owner_id = %s"
                        values.extend([business_id, user_id])
                    else:
                        update_sql = f"UPDATE businesses SET {set_clause} WHERE id = %s"
                        values.append(business_id)

                    cur.execute(update_sql, values)

                # Update business categories
                cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))
                for cat_id in selected_category_ids:
                    if cat_id:
                        cur.execute("""
                            INSERT INTO business_categories (business_id, category_id)
                            VALUES (%s, %s)
                        """, (business_id, cat_id))

                conn.commit()
                flash('Business updated successfully!', 'success')
                return redirect(url_for('user.business_profile', business_id=business_id))

            # Load subscription plans
            cur.execute("SELECT * FROM subscription_plans ORDER BY amount ASC")
            subscription_plans = cur.fetchall()

        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            flash(f'Error updating business: {str(e)}', 'error')
        finally:
            conn.close()

    context = {
        "business": business,
        "subscription_plans": subscription_plans,
        "all_categories": all_categories,
        "business_categories": business_categories,
        "business_category_ids": business_category_ids
    }

    return render_template('business/account_profile.html', **context)


# @bp.route('/business/<int:business_id>/public')
# def public_business_profile(business_id):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
        
#         # Get business details with categories
#         cur.execute("""
#             SELECT 
#                 b.*,
#                 u.username as owner_username,
#                 GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories
#             FROM businesses b
#             LEFT JOIN users u ON b.owner_id = u.id
#             LEFT JOIN business_categories bc ON b.id = bc.business_id
#             LEFT JOIN categories c ON bc.category_id = c.id
#             WHERE b.id = %s AND b.status = 'active'
#             GROUP BY b.id
#         """, (business_id,))
        
#         business = cur.fetchone()
        
#         if not business:
#             flash("Currently not running Ads. If you're the owner, Subscribe to a plan to make your business page accessible.", 'error')
#             return redirect(url_for('index.home'))
        
#         # Get similar businesses (same category)
#         cur.execute("""
#             SELECT b.id, b.business_name, b.media_url, b.media_type
#             FROM businesses b
#             JOIN business_categories bc ON b.id = bc.business_id
#             WHERE bc.category_id IN (
#                 SELECT category_id FROM business_categories 
#                 WHERE business_id = %s
#             )
#             AND b.id != %s
#             AND b.status = 'active'
#             GROUP BY b.id
#             LIMIT 4
#         """, (business_id, business_id))
        
#         similar_businesses = cur.fetchall()
        
#         return render_template('business/public_profile.html',
#                             business=business,
#                             similar_businesses=similar_businesses,
#                             is_owner=('user_id' in session and 
#                                      session['user_id'] == business['owner_id']))
        
#     except Exception as e:
#         app.logger.error(f"Error loading business profile: {str(e)}")
#         traceback.print_exception(e)
#         flash('Error loading business profile', 'error')
#         return redirect(url_for('index.home'))
#     finally:
#         if conn:
#             conn.close()

# v2 - use slug url instead
@bp.route("/business/<string:business_slug>")
def public_business_profile(business_slug):
    """Public business profile (slug-based)"""

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
                b.*,
                u.username AS owner_username,
                GROUP_CONCAT(DISTINCT c.category_name) AS categories
            FROM businesses b
            LEFT JOIN users u ON b.owner_id = u.id
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.slug = %s
              AND b.status = 'active'
            GROUP BY b.id
        """, (business_slug,))
        business = cur.fetchone()

        if not business:
            flash(
                "This business is currently unavailable.",
                "error"
            )
            return redirect(url_for("index.home"))

        # Similar businesses
        cur.execute("""
            SELECT
                b.business_name,
                b.slug,
                b.media_url,
                b.media_type
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            WHERE bc.category_id IN (
                SELECT category_id
                FROM business_categories
                WHERE business_id = %s
            )
              AND b.id != %s
              AND b.status = 'active'
            GROUP BY b.id
            LIMIT 4
        """, (business["id"], business["id"]))
        
        seo = build_seo(
        title=f'{business["business_name"]} in Ajah, Lagos',
        description=f'{business["business_name"]} is a trusted {business["categories"]} business in Ajah, Lagos.',
        image=business.get("media_url"),
        schema=business_schema(business),
    )

        similar_businesses = cur.fetchall()

        return render_template(
            "business/public_profile.html",
            business=business,
            seo=seo,
            similar_businesses=similar_businesses,
            is_owner=session.get("user_id") == business["owner_id"],
        )

    except Exception:
        app.logger.exception("Public business profile error")
        flash("Unable to load business profile.", "error")
        return redirect(url_for("index.home"))
    finally:
        if conn:
            conn.close()


@bp.route('/search-business')
def search_business():
    """Search businesses by name, category, or shop number"""
    search_query = request.args.get('search_query', '').strip()
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', None)
    
    if not search_query and not category_filter:
        flash('Please enter a search term or select a category', 'info')
        return redirect(url_for('index.home'))
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Pagination settings
        per_page = 12
        offset = (page - 1) * per_page
        
        # Base query with joins
        base_query = """
            SELECT 
                b.*,
                u.username as owner_username,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
                COUNT(DISTINCT c.id) as category_count,
                MIN(c.category_name) as primary_category,
                CASE 
                    WHEN b.status = 'active' THEN 0 
                    WHEN b.status = 'pending' THEN 1
                    ELSE 2 
                END as status_order
            FROM businesses b
            LEFT JOIN users u ON b.owner_id = u.id
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.status != 'deleted'
        """
        
        # Count query (simpler version without all the fields)
        count_query = """
            SELECT COUNT(DISTINCT b.id) as total
            FROM businesses b
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.status != 'deleted'
        """
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_query:
            condition = """
                (b.business_name LIKE %s OR 
                b.description LIKE %s OR 
                b.shop_no LIKE %s OR 
                c.category_name LIKE %s)
            """
            conditions.append(condition)
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if category_filter:
            conditions.append("c.id = %s")
            params.append(category_filter)
        
        if conditions:
            where_clause = " AND " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Add grouping and ordering to main query
        base_query += """
            GROUP BY b.id
            ORDER BY b.is_subscribed DESC, 
                     status_order,
                     b.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        # Execute count query
        cur.execute(count_query, params)
        total = cur.fetchone()['total']
        
        # Add pagination params
        params.extend([per_page, offset])
        
        # Execute main query
        cur.execute(base_query, params)
        businesses = cur.fetchall()
        
        # Process the businesses data
        for biz in businesses:
            biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
        # Get all categories for filter dropdown
        cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
        all_categories = cur.fetchall()
        
        return render_template('search_results.html', 
                            businesses=businesses,
                            search_query=search_query,
                            selected_category=category_filter,
                            all_categories=all_categories,
                            username=session.get('username'),
                            user_profile=session.get('profile_image'),
                            pagination={
                                'page': page,
                                'per_page': per_page,
                                'total': total,
                                'has_next': offset + per_page < total,
                                'has_prev': page > 1
                            })

    except Exception as e:
        traceback.print_exc()
        app.logger.error(f"Search error: {str(e)}")
        flash('Error performing search. Please try again later.', 'error')
        return redirect(url_for('index.home'))
    finally:
        if conn:
            conn.close()

@bp.route('/add-business', methods=['GET', 'POST'])
def add_business():
    """Add new business with integrated status handling"""
    if 'user_id' not in session:
        flash('Please log in to add a business.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        conn = get_db_connection()
        try:
            # Get form data
            business_name = request.form.get('business_name')
            description = request.form.get('description')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email')
            shop_no = request.form.get('shop_no')
            block_num = request.form.get('block_num')
            address = request.form.get('address')

            website_url = request.form.get('website_url')
            facebook_link = request.form.get('facebook_link')
            instagram_link = request.form.get('instagram_link')
            twitter_link = request.form.get('twitter_link')

            file = request.files.get('business_media')
            # category_ids = request.form.getlist('categories')
            
            custom_categories = request.form.get('custom_categories')
            category_ids = request.form.getlist('categories')

            # Remove 'other' from category IDs
            category_ids = [cid for cid in category_ids if cid != 'other']
            
            
            base_slug = slugify(business_name)


            cur = conn.cursor()
            
            slug = generate_unique_slug(cur, base_slug)



            # Handle media upload
            media_url = None
            media_type = None
            if file and file.filename:
                media_url = upload_file(file)
                media_type = 'image'  # Default to image type

            # Insert new business with 'pending' status
            # cur = conn.cursor()
            # cur.execute("""
            #     INSERT INTO businesses (
            #         owner_id, business_name, description,
            #         phone_number, email, shop_no, block_num, address,
            #         website_url, facebook_link, instagram_link, twitter_link, 
            #         media_type, media_url, status
            #     ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            # """, (
            #     user_id, business_name, description,
            #     phone_number, email, shop_no, block_num, address,
            #     website_url, facebook_link, instagram_link, twitter_link, 
            #     media_type, media_url
            # ))
            
            cur.execute("""
                INSERT INTO businesses (
                    owner_id, business_name, slug, description,
                    phone_number, email, shop_no, block_num, address,
                    website_url, facebook_link, instagram_link, twitter_link,
                    custom_categories, media_type, media_url, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                user_id, business_name, slug, description,
                phone_number, email, shop_no, block_num, address,
                website_url, facebook_link, instagram_link, twitter_link,
                custom_categories, media_type, media_url
            ))

            # Get the newly created business ID
            business_id = cur.lastrowid

            # Create category relationships
            for category_id in category_ids:
                cur.execute("""
                    INSERT INTO business_categories (business_id, category_id)
                    VALUES (%s, %s)
                """, (business_id, category_id))
            
            conn.commit()
            flash('Business submitted for approval!', 'success')
            return redirect(url_for('user.profile'))

        except Exception as e:
            conn.rollback()
            flash(f'Error adding business: {str(e)}', 'error')
            # Get categories again to render the form with errors
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
            categories = cur.fetchall()
            return render_template('business/add_business.html', categories=categories)
        finally:
            if conn:
                conn.close()

    # GET request - fetch categories
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
        categories = cur.fetchall()
    except Exception as e:
        flash(f'Error loading categories: {str(e)}', 'error')
        categories = []
    finally:
        if conn:
            conn.close()

    return render_template('business/add_business.html', categories=categories)


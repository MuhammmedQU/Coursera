from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Database file path
DATABASE = 'users.db'
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@abituriyent.ai')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


# ===== DATABASE FUNCTIONS =====
def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database and create tables if they don't exist"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP
            )
        ''')
        
        # Create admin table for admin credentials
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("[DB] Database tables initialized successfully")
    except Exception as e:
        print(f"[DB ERROR] Failed to initialize database: {e}")


def migrate_from_json():
    """Migrate existing users from users.json to database (run only once)"""
    if not os.path.exists('users.json'):
        print("[DB] No users.json file found, skipping migration")
        return
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        migrated_count = 0
        for user in users:
            try:
                cursor.execute('''
                    INSERT INTO users (email, password, status)
                    VALUES (?, ?, ?)
                ''', (user['email'], user['password'], user.get('status', 'pending')))
                migrated_count += 1
            except sqlite3.IntegrityError:
                # User already exists, skip
                pass
        
        conn.commit()
        conn.close()
        print(f"[DB] Successfully migrated {migrated_count} users from users.json")
    except Exception as e:
        print(f"[DB ERROR] Error migrating from JSON: {e}")


def create_admin_user():
    """Create default admin user if it doesn't exist"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        hashed_password = generate_password_hash(ADMIN_PASSWORD)
        cursor.execute('''
            INSERT INTO admin_users (email, password)
            VALUES (?, ?)
        ''', (ADMIN_EMAIL, hashed_password))
        conn.commit()
        conn.close()
        print(f"[DB] Admin user created: {ADMIN_EMAIL}")
    except sqlite3.IntegrityError:
        # Admin already exists
        print(f"[DB] Admin user already exists: {ADMIN_EMAIL}")
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Error creating admin user: {e}")
        try:
            conn.close()
        except:
            pass


def get_user_by_email(email):
    """Get user from database by email"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def add_user(email, password, status='pending'):
    """Add new user to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (email, password, status)
            VALUES (?, ?, ?)
        ''', (email, hashed_password, status))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    finally:
        conn.close()
    
    return result


def get_all_users():
    """Get all users from database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, status, created_at, approved_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return users


def update_user_status(user_id, status):
    """Update user status (approved/pending/rejected)"""
    conn = get_db()
    cursor = conn.cursor()
    
    if status == 'approved':
        cursor.execute('''
            UPDATE users SET status = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, user_id))
    else:
        cursor.execute('''
            UPDATE users SET status = ?
            WHERE id = ?
        ''', (status, user_id))
    
    conn.commit()
    conn.close()


def delete_user(user_id):
    """Delete user from database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def verify_admin(email, password):
    """Verify admin credentials"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE email = ?', (email,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin and check_password_hash(admin['password'], password):
        return True
    return False


# ===== ROUTES =====
@app.route('/')
def index():
    """Public landing page"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        
        # Check if user exists and password matches
        if user and check_password_hash(user['password'], password):
            # Check if user status is approved
            if user['status'] == 'pending':
                return render_template('login.html', error="Your account is pending approval. Please wait for the admin to grant you access. Contact the admin with your email to request access.")
            elif user['status'] == 'rejected':
                return render_template('login.html', error="Your account has been rejected. Please contact the admin.")
            
            # User is approved, proceed with login
            session['email'] = email
            return redirect(url_for('video'))
        else:
            return render_template('login.html', error="Invalid email or password - access denied")
    
    success = request.args.get('success')
    return render_template('login.html', success=success)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup/Registration page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        if get_user_by_email(email):
            return render_template('signup.html', error="Email already registered")
        
        # Add new user with pending status
        if add_user(email, password, 'pending'):
            # Redirect to login with success message
            return redirect(url_for('login', success="Registration successful! Your account is pending admin approval. Please wait until you're granted access."))
        else:
            return render_template('signup.html', error="Error during registration. Please try again.")
    
    return render_template('signup.html')


@app.route('/video')
def video():
    """Protected video page"""
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # Verify user is still approved
    user = get_user_by_email(session['email'])
    if not user or user['status'] != 'approved':
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('video.html', email=session['email'])


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))


# ===== ADMIN ROUTES =====
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if verify_admin(email, password):
            session['admin_email'] = email
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Invalid email or password")
    
    return render_template('admin_login.html')


@app.route('/admin/panel')
def admin_panel():
    """Admin panel - manage users"""
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    users = get_all_users()
    return render_template('admin_panel.html', users=users, admin_email=session['admin_email'])


@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    """Approve a user"""
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    update_user_status(user_id, 'approved')
    return redirect(url_for('admin_panel'))


@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    """Reject a user"""
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    update_user_status(user_id, 'rejected')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    """Delete a user"""
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    delete_user(user_id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    return redirect(url_for('admin_login'))


# ===== APPLICATION INITIALIZATION =====
# Initialize database (runs on app startup - works with both Flask dev server and Gunicorn)
print("[STARTUP] Initializing database...")
init_db()
print("[STARTUP] Creating admin user...")
create_admin_user()
print("[STARTUP] Migrating users from JSON...")
migrate_from_json()
print("[STARTUP] Application initialized successfully!\n")


# Backup initialization handler (in case module-level initialization doesn't run)
@app.before_request
def ensure_db_initialized():
    """Ensure database is initialized before handling any request"""
    if not os.path.exists(DATABASE):
        print("[STARTUP] Database not found, running initialization...")
        init_db()
        create_admin_user()
        migrate_from_json()


if __name__ == '__main__':
    # Local development only
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

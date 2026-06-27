from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                video_id INTEGER NOT NULL,
                watched INTEGER DEFAULT 0,
                watched_at TIMESTAMP,
                UNIQUE(email, video_id)
            )
        ''')

        conn.commit()
        conn.close()
        print("[DB] Database tables initialized successfully")
    except Exception as e:
        print(f"[DB ERROR] Failed to initialize database: {e}")


def migrate_from_json():
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
                pass

        conn.commit()
        conn.close()
        print(f"[DB] Successfully migrated {migrated_count} users from users.json")
    except Exception as e:
        print(f"[DB ERROR] Error migrating from JSON: {e}")


def create_admin_user():
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
        print(f"[DB] Admin user already exists: {ADMIN_EMAIL}")
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Error creating admin user: {e}")
        try:
            conn.close()
        except:
            pass


def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def add_user(email, password, status='pending'):
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, status, created_at, approved_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return users


def update_user_status(user_id, status):
    conn = get_db()
    cursor = conn.cursor()
    if status == 'approved':
        cursor.execute('''
            UPDATE users SET status = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, user_id))
    else:
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def verify_admin(email, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE email = ?', (email,))
    admin = cursor.fetchone()
    conn.close()
    if admin and check_password_hash(admin['password'], password):
        return True
    return False


def get_user_progress(email):
    """Get watched video IDs for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT video_id FROM video_progress WHERE email = ? AND watched = 1', (email,))
    rows = cursor.fetchall()
    conn.close()
    return [row['video_id'] for row in rows]


def mark_video_watched(email, video_id):
    """Mark a video as watched for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO video_progress (email, video_id, watched, watched_at)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(email, video_id) DO UPDATE SET watched = 1, watched_at = CURRENT_TIMESTAMP
    ''', (email, video_id))
    conn.commit()
    conn.close()


# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            if user['status'] == 'pending':
                return render_template('login.html', error="Hesabınız hələ təsdiqlənməyib. Admin təsdiqini gözləyin.")
            elif user['status'] == 'rejected':
                return render_template('login.html', error="Hesabınız rədd edilib. Adminlə əlaqə saxlayın.")

            session['email'] = email
            session['is_new_login'] = True  # Flag for welcome message
            return redirect(url_for('video'))
        else:
            return render_template('login.html', error="Yanlış email və ya şifrə - giriş rədd edildi")

    success = request.args.get('success')
    return render_template('login.html', success=success)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if get_user_by_email(email):
            return render_template('signup.html', error="Bu email artıq qeydiyyatdan keçib")

        if add_user(email, password, 'pending'):
            return redirect(url_for('login', success="Qeydiyyat uğurlu oldu! Admin təsdiqini gözləyin."))
        else:
            return render_template('signup.html', error="Qeydiyyat zamanı xəta baş verdi. Yenidən cəhd edin.")

    return render_template('signup.html')


@app.route('/video')
def video():
    if 'email' not in session:
        return redirect(url_for('login'))

    user = get_user_by_email(session['email'])
    if not user or user['status'] != 'approved':
        session.clear()
        return redirect(url_for('login'))

    # Get progress and welcome flag
    progress = get_user_progress(session['email'])
    is_new_login = session.pop('is_new_login', False)

    return render_template('video.html',
                           email=session['email'],
                           progress=progress,
                           is_new_login=is_new_login)


@app.route('/video/watched/<int:video_id>', methods=['POST'])
def mark_watched(video_id):
    """Mark a video as watched - called via JS"""
    if 'email' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    mark_video_watched(session['email'], video_id)
    return jsonify({'success': True})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ===== ADMIN ROUTES =====
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if verify_admin(email, password):
            session['admin_email'] = email
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error="Yanlış email və ya şifrə")

    return render_template('admin_login.html')


@app.route('/admin/panel')
def admin_panel():
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    users = get_all_users()
    return render_template('admin_panel.html', users=users, admin_email=session['admin_email'])


@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    update_user_status(user_id, 'approved')
    return redirect(url_for('admin_panel'))


@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    update_user_status(user_id, 'rejected')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    delete_user(user_id)
    return redirect(url_for('admin_panel'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


# ===== APPLICATION INITIALIZATION =====
print("[STARTUP] Initializing database...")
init_db()
print("[STARTUP] Creating admin user...")
create_admin_user()
print("[STARTUP] Migrating users from JSON...")
migrate_from_json()
print("[STARTUP] Application initialized successfully!\n")


@app.before_request
def ensure_db_initialized():
    if not os.path.exists(DATABASE):
        print("[STARTUP] Database not found, running initialization...")
        init_db()
        create_admin_user()
        migrate_from_json()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
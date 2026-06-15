from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Load users from JSON file
def load_users():
    with open('users.json', 'r') as f:
        return json.load(f)

# Save users to JSON file
def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

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
        
        users = load_users()
        
        # Check if user exists and password matches
        user_found = None
        for user in users:
            if user['email'] == email and check_password_hash(user['password'], password):
                user_found = user
                break
        
        if user_found:
            # Check if user status is approved
            if user_found.get('status') == 'pending':
                return render_template('login.html', error="Your account is pending approval. Please wait for the admin to grant you access. Contact the admin with your email to request access.")
            
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
        
        users = load_users()
        
        # Check if email already exists
        for user in users:
            if user['email'] == email:
                return render_template('signup.html', error="Email already registered")
        
        # Hash password and add new user with pending status
        hashed_password = generate_password_hash(password)
        new_user = {"email": email, "password": hashed_password, "status": "pending"}
        users.append(new_user)
        save_users(users)
        
        # Redirect to login with success message
        return redirect(url_for('login', success="Registration successful! Your account is pending admin approval. Please wait until you're granted access."))
    
    return render_template('signup.html')

@app.route('/video')
def video():
    """Protected video page"""
    if 'email' not in session:
        return redirect(url_for('login'))
    
    return render_template('video.html', email=session['email'])

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

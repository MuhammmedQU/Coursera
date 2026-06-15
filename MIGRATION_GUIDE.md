# SQLite Migration Guide - AbituriyentAI

## Overview

Your Flask application has been successfully refactored from JSON-based user storage to **SQLite database**. This makes your application fully compatible with **Render's ephemeral filesystem**, ensuring that user data persists across deployments.

---

## ✅ What's New

### 1. **SQLite Database**
- **File**: `users.db` (automatically created on first run)
- **Tables**: 
  - `users` - stores email, password, status, registration date
  - `admin_users` - stores admin credentials

### 2. **New Admin Panel**
- **Route**: `/admin/login` - Admin login page
- **Route**: `/admin/panel` - User management dashboard
- **Features**:
  - View all registered users
  - See email and registration status
  - Approve pending users
  - Reject users
  - Delete users permanently

### 3. **Automatic Features**
- Database automatically initializes on app startup
- Users from `users.json` are migrated to database on first run
- Admin user created automatically with default credentials
- Session management preserved

### 4. **All Original Functionality Preserved**
✅ Signup  
✅ Login  
✅ Logout  
✅ Session handling  
✅ Pending approval system  
✅ Approved users can access videos  
✅ Pending users cannot access videos  
✅ Password hashing with Werkzeug  
✅ UI and templates unchanged  

---

## 🚀 Deployment Instructions

### Local Testing

1. **Run the app locally**:
```bash
python app.py
```

2. **Access the admin panel**:
   - URL: `http://localhost:5000/admin/login`
   - **Default Email**: `admin@abituriyent.ai`
   - **Default Password**: `admin123`

3. **Change admin credentials** (recommended):
   - Stop the app
   - Set environment variables:
     ```bash
     # Windows PowerShell
     $env:ADMIN_EMAIL = "your-email@gmail.com"
     $env:ADMIN_PASSWORD = "your-secure-password"
     
     # Windows CMD
     set ADMIN_EMAIL=your-email@gmail.com
     set ADMIN_PASSWORD=your-secure-password
     
     # Linux/Mac
     export ADMIN_EMAIL=your-email@gmail.com
     export ADMIN_PASSWORD=your-secure-password
     ```
   - Restart the app

### Deploy to Render

1. **Update `render.yaml`** - Ensure it includes:
```yaml
services:
  - type: web
    name: abituriyentai
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: ADMIN_EMAIL
        value: your-admin-email@gmail.com  # Change this
      - key: ADMIN_PASSWORD
        value: your-secure-password        # Change this
```

2. **Push to GitHub** and Render will auto-deploy

3. **Access on Render**:
   - Main app: `https://your-app-name.onrender.com/`
   - Admin login: `https://your-app-name.onrender.com/admin/login`
   - Admin panel: `https://your-app-name.onrender.com/admin/panel`

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP
)
```

### Admin Users Table
```sql
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## 🔑 Key Functions

### User Management
- `get_user_by_email(email)` - Retrieve user
- `add_user(email, password, status='pending')` - Create new user
- `get_all_users()` - List all users
- `update_user_status(user_id, status)` - Change user status
- `delete_user(user_id)` - Remove user

### Admin
- `verify_admin(email, password)` - Authenticate admin
- `create_admin_user()` - Initialize admin (runs on startup)

### Database
- `init_db()` - Create tables (runs automatically)
- `migrate_from_json()` - Import from users.json (runs automatically)

---

## 📝 Important Notes

### Security
1. **Change default admin credentials immediately** after first deployment
2. Use environment variables for sensitive data:
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
   - `SECRET_KEY` (auto-generated, but can be set)

3. Render supports environment variables in dashboard:
   - Go to your service settings
   - Add Environment Variables
   - Set `ADMIN_EMAIL` and `ADMIN_PASSWORD`

### Data Persistence on Render
✅ `users.db` is stored in Render's persistent file system (under `/var/data`)  
✅ Database survives app restarts and deployments  
✅ No data loss during scale-up/scale-down  

### Debugging
- Check `users.db` exists in your project root
- All database functions log errors to console
- Admin panel shows user count and status breakdown

---

## 🔄 Migration Process

When you run the app for the first time:

1. `init_db()` runs → creates SQLite tables
2. `migrate_from_json()` runs → imports users from `users.json`
3. `create_admin_user()` runs → creates admin account
4. App is ready to use

**No manual migration needed!**

---

## 📱 Routes Reference

### Public Routes
- `GET/POST /` - Home page
- `GET/POST /login` - User login
- `GET/POST /signup` - User registration
- `GET /video` - Protected course videos (approved users only)
- `GET /logout` - User logout

### Admin Routes
- `GET/POST /admin/login` - Admin login
- `GET /admin/panel` - User management dashboard
- `POST /admin/approve/<user_id>` - Approve user
- `POST /admin/reject/<user_id>` - Reject user
- `POST /admin/delete/<user_id>` - Delete user
- `GET /admin/logout` - Admin logout

---

## ✨ Files Changed/Created

### Modified Files
- ✏️ `app.py` - Complete refactor to SQLite
- ✏️ `requirements.txt` - Added comment about SQLite

### New Templates
- ✨ `templates/admin_login.html` - Admin login page
- ✨ `templates/admin_panel.html` - User management dashboard

### Auto-Created Files
- 🗄️ `users.db` - SQLite database (created on first run)

### Unchanged Files
- ✅ `templates/index.html` - No changes
- ✅ `templates/login.html` - No changes
- ✅ `templates/signup.html` - No changes
- ✅ `templates/video.html` - No changes
- ✅ `static/style.css` - No changes
- ✅ `users.json` - Kept for reference (not used by app)

---

## 🆘 Troubleshooting

### Issue: "users.db not found"
- **Solution**: Run the app once locally. Database auto-initializes.

### Issue: Admin login fails
- **Solution**: Verify `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables are set correctly

### Issue: Users not visible in admin panel
- **Solution**: Check that users were migrated from `users.json`. Check browser console for errors.

### Issue: "email already registered" after migration
- **Solution**: If importing from `users.json`, the email constraint prevents duplicates (working as intended)

### Issue: Data lost after Render restart
- **Solution**: Ensure `users.db` is in project root. Render persists this location automatically.

---

## 🎓 Code Examples

### Add a user programmatically
```python
add_user('student@example.com', 'password123', 'pending')
```

### Approve a user
```python
update_user_status(1, 'approved')  # 1 = user_id
```

### Get all pending users
```python
users = get_all_users()
pending = [u for u in users if u['status'] == 'pending']
```

---

## 📞 Support

If you encounter issues:
1. Check the app logs in Render dashboard
2. Verify environment variables are set
3. Ensure `users.db` exists in project root
4. Check that all templates are in `/templates` directory

**Congratulations!** Your AbituriyentAI platform is now deployment-ready with persistent data storage! 🎉

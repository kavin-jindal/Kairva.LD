from app import app, csrf
from flask import render_template, request, jsonify, session, redirect, url_for
from app.firebase_config import verify_token, auth
from app.db import get_user, upsert_user, get_users_by_role, update_user_status, create_job, get_jobs, delete_user_db, get_market_insights, get_all_jobs_admin, update_job_verification, delete_job_db, get_job_by_id
from functools import wraps
from flask import abort
import os
from werkzeug.utils import secure_filename
from app.supabase_storage import get_signed_url as get_supabase_signed_url

@app.context_processor
def utility_processor():
    def resolve_url(path):
        return resolve_url_py(path)
    return dict(resolve_url=resolve_url)

def resolve_url_py(path):
    if not path:
        return ""
    if path.startswith('supabase://'):
        signed_url = get_supabase_signed_url(path)
        return signed_url if signed_url else ""
    if path.startswith('http'):
        return path
    return url_for('static', filename=path)

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or session['user'].get('role') != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", user=session.get('user'))

@app.errorhandler(403)
def forbidden(e):
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

@app.route("/login")
def login():
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'company':
             return redirect(url_for('company_dashboard'))
        elif role == 'admin':
             return redirect(url_for('admin_dashboard'))
        else:
             return redirect(url_for('student_dashboard'))
    return render_template("login.html")

@app.route("/register")
def register():
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'company':
             return redirect(url_for('company_dashboard'))
        elif role == 'admin':
             return redirect(url_for('admin_dashboard'))
        else:
             return redirect(url_for('student_dashboard'))
    return render_template("register.html")

@app.route("/for-companies")
def for_companies():
    return render_template("for-companies.html")

@app.route("/about")
def about():
    return render_template("about.html", user=session.get('user'))

@app.route("/company/login")
def company_login():
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'company':
             return redirect(url_for('company_dashboard'))
        elif role == 'admin':
             return redirect(url_for('admin_dashboard'))
        else:
             return redirect(url_for('student_dashboard'))
    return render_template("company-login.html")

@app.route("/company/register")
def company_register():
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'company':
             return redirect(url_for('company_dashboard'))
        elif role == 'admin':
             return redirect(url_for('admin_dashboard'))
        else:
             return redirect(url_for('student_dashboard'))
    return render_template("company-register.html")

@app.route("/admin/login")
def admin_login():
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'company':
             return redirect(url_for('company_dashboard'))
        elif role == 'admin':
             return redirect(url_for('admin_dashboard'))
        else:
             return redirect(url_for('student_dashboard'))
    return render_template("admin-login.html")


@app.route("/verify-token", methods=['POST'])
@csrf.exempt
def verify_google_token():
    try:
        data = request.json
        id_token = data.get('token')
        role_requested = data.get('role', 'student')
        name_requested = data.get('name')
        
        print(f"DEBUG: Verifying token for role: {role_requested}")
        decoded_token, error_msg = verify_token(id_token)
        
        if decoded_token:
            uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            print(f"DEBUG: Token verified for email: {email}")
            
            # Use centralized Admin emails from config
            ADMIN_EMAILS = app.config.get('ADMIN_EMAILS', [])
            
            # Check SQLite for user profile
            user_data = get_user(uid)
            
            # Determine role and redirection
            if user_data:
                role = user_data.get('role', 'student')
                
                # Verification logic: admin role is sticky and protected
                if email in ADMIN_EMAILS:
                    role = 'admin'
                elif role == 'admin' and email not in ADMIN_EMAILS:
                    # Downgrade if no longer on whitelist (failsafe)
                    role = 'student'
                    
                # Fix: Role requested by client should only be honored for new users 
                # or when explicitly allowed (e.g., student -> company transition)
                if role_requested == 'company' and role == 'student':
                    role = 'company'
                    upsert_user(uid, {'role': 'company'})
                
                session['user'] = {
                    'uid': uid,
                    'email': email,
                    'name': user_data.get('name') or decoded_token.get('name') or '',
                    'role': role,
                    'is_verified': 1 if user_data.get('is_verified') else 0
                }
                session['profile_completed'] = True
                
                # Redirect based on role
                if role == 'admin':
                    redirect_url = url_for('admin_dashboard')
                elif role == 'company':
                    redirect_url = url_for('company_dashboard')
                else:
                    redirect_url = url_for('student_dashboard')
            else:
                # New user logic
                # Prioritize name from request body (Email/Pass registration), fallback to Google decodetoken name
                user_name = name_requested or decoded_token.get('name') or ''
                
                # Default to student, escalate only if on admin whitelist
                role = 'student'
                if email in ADMIN_EMAILS:
                    role = 'admin'
                elif role_requested == 'company':
                    role = 'company'
                
                print(f"DEBUG: Creating new user: {email} with role: {role}")
                session['user'] = {
                    'uid': uid,
                    'email': email,
                    'name': user_name,
                    'role': role,
                    'is_verified': 1 if role == 'student' else 0
                }
                
                # Save basic profile record
                profile_data = {
                    'name': user_name,
                    'email': email,
                    'role': role,
                    'is_verified': 1 if role == 'student' else 0
                }
                upsert_user(uid, profile_data)
                
                if role == 'company':
                    session['profile_completed'] = True
                    redirect_url = url_for('company_dashboard')
                elif role == 'admin':
                    session['profile_completed'] = True
                    redirect_url = url_for('admin_dashboard')
                else:
                    session['profile_completed'] = False
                    redirect_url = url_for('complete_profile')
            
            print(f"DEBUG: Login successful for {email}, redirecting to: {redirect_url}")
            return jsonify({'success': True, 'redirect_url': redirect_url}), 200
        else:
            print(f"DEBUG: Token verification failed internally: {error_msg}")
            return jsonify({'success': False, 'error': 'Verification failed. Please try again.'}), 401
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR IN VERIFY-TOKEN: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'An internal server error occurred.'}), 500

@app.route("/complete-profile", methods=['GET', 'POST'])
def complete_profile():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    uid = session['user']['uid']
        
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name', '').strip()
        
        # Validation: Name is compulsory
        if not name:
            user_data = get_user(uid)
            display_data = session['user'].copy()
            if user_data:
                display_data.update(user_data)
            return render_template("complete-profile.html", user=display_data, error="Full Name is required.")

        profile_data = {
            'enrollment_number': request.form.get('enrollment_number'),
            'branch': request.form.get('branch'),
            'admission_year': request.form.get('admission_year'),
            'passout_year': request.form.get('passout_year'),
            'study_type': request.form.get('study_type'),
            'cpi': request.form.get('cpi'),
            'skills': request.form.get('skills'),
            'name': name, # Use validated name
            'email': session['user'].get('email'),
            'role': session['user'].get('role', 'student'),
            'linkedin_url': request.form.get('linkedin_url'),
            'github_url': request.form.get('github_url'),
            'portfolio_url': request.form.get('portfolio_url')
        }
        
        # Handle Resume Upload (Supabase Storage)
        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename != '':
            if resume_file.filename.lower().endswith('.pdf'):
                try:
                    from app.supabase_storage import upload_resume
                    file_data = resume_file.read()
                    public_url = upload_resume(uid, file_data, resume_file.filename)
                    profile_data['resume_path'] = public_url
                except Exception as e:
                    print(f"Error uploading resume to Supabase: {e}")
        
        # Handle Profile Picture Upload (Supabase Storage)
        profile_pic_file = request.files.get('profile_pic')
        if profile_pic_file and profile_pic_file.filename != '':
            allowed_extensions = {'.png', '.jpg', '.jpeg'}
            file_ext = os.path.splitext(profile_pic_file.filename)[1].lower()
            if file_ext in allowed_extensions:
                try:
                    from app.supabase_storage import upload_profile_pic
                    file_data = profile_pic_file.read()
                    public_url = upload_profile_pic(uid, file_data, profile_pic_file.filename)
                    profile_data['profile_pic'] = public_url
                except Exception as e:
                    print(f"Error uploading profile pic to Supabase: {e}")
        
        # Save to SQLite
        upsert_user(uid, profile_data)
        
        # Sync name with Firebase Auth
        try:
            auth.update_user(
                uid,
                display_name=profile_data['name']
            )
        except Exception as e:
            print(f"Error updating Firebase user: {e}")
        
        # Update session identity
        session['user']['name'] = profile_data['name']
        session['profile_completed'] = True
        session.modified = True
        
        if profile_data['role'] == 'company':
            return redirect(url_for('company_dashboard'))
        return redirect(url_for('student_dashboard'))
    
    # Pre-fill form if data exists
    user_data = get_user(uid)
    display_data = session['user'].copy()
    if user_data:
        display_data.update(user_data)
    
    return render_template("complete-profile.html", user=display_data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/student-dashboard")
@role_required('student')
def student_dashboard():
    # Fetch fresh data from DB
    uid = session['user']['uid']
    user_data = get_user(uid)
    
    # Merge session identity with DB profile
    display_user = session['user'].copy()
    if user_data:
        display_user.update(user_data)
        
    from app.db import get_applications, get_jobs
    applications = get_applications(student_uid=uid)
    jobs = get_jobs()
    
    applied_job_ids = [app['job_id'] for app in applications]
    
    
    # Get active section from URL
    section = request.args.get('section', 'overview')
        
    # Calculate profile completion dynamically
    # For students, let's say name, email (always present via auth), branch, and skills are required
    is_profile_complete = False
    if user_data:
        is_profile_complete = all([
            user_data.get('branch'),
            user_data.get('skills'),
            user_data.get('enrollment_number')
        ])
    
    session['profile_completed'] = is_profile_complete
        
    return render_template("student-dashboard.html", 
                         user=display_user, 
                         profile_completed=is_profile_complete, 
                         applications=applications,
                         jobs=jobs,
                         active_section=section,
                         applied_job_ids=applied_job_ids)


@app.route("/placement-records")
def placement_records():
    # Handle user session if logged in
    display_user = None
    if 'user' in session:
        uid = session['user']['uid']
        user_data = get_user(uid)
        
        # Merge session identity with DB profile
        display_user = session['user'].copy()
        if user_data:
            display_user.update(user_data)
        
    # Historical Placement Data
    historical_data = {
        "analysis_metadata": {
            "total_records": 316,
            "primary_sector": "Industrial Automation, Oil & Gas",
            "mode": "94% Offline"
        },
        "overall_top_internships": [
            {"company": "IFFCO", "count": 49},
            {"company": "ONGC", "count": 27},
            {"company": "GNFC", "count": 9},
            {"company": "Cess Automation", "count": 7},
            {"company": "Axis Solutions", "count": 7},
            {"company": "Pima Controls", "count": 6},
            {"company": "IGTR Ahmedabad", "count": 5},
            {"company": "Banas Dairy", "count": 5},
            {"company": "Iris Automation", "count": 4},
            {"company": "HPCL", "count": 4}
        ],
        "last_year_top_internships": [
            {"company": "IFFCO", "count": 19},
            {"company": "ONGC", "count": 10},
            {"company": "HPCL", "count": 4},
            {"company": "Iris Automation", "count": 4},
            {"company": "Pima Controls", "count": 3},
            {"company": "GSECL", "count": 3},
            {"company": "Spark Solution", "count": 2},
            {"company": "IOCL", "count": 2},
            {"company": "GNFC", "count": 2},
            {"company": "Banas Dairy", "count": 2}
        ]
    }
    
    return render_template("placement-records.html", 
                         user=display_user, 
                         data=historical_data,
                         profile_completed=session.get('profile_completed'))


@app.route("/profile")
@role_required('student')
def profile():
    # Fetch fresh data from DB
    uid = session['user']['uid']
    user_data = get_user(uid)
    
    # Merge session identity with DB profile
    display_user = session['user'].copy()
    if user_data:
        display_user.update(user_data)
        
    return render_template("profile_view.html", user=display_user)

@app.route("/company-dashboard")
@role_required('company')
def company_dashboard():
    uid = session['user']['uid']
    user_data = get_user(uid)
    from app.db import get_jobs, get_applications
    jobs = get_jobs(uid)
    applications = [app for app in get_applications(company_uid=uid) if app['status'] != 'withdrawn']
    
    # Pre-resolve URLs for JS modals and templates
    for app_data in applications:
        app_data['profile_pic'] = resolve_url_py(app_data.get('profile_pic'))
        app_data['resume_path'] = resolve_url_py(app_data.get('resume_path'))
        
    return render_template("company-dashboard.html", user=user_data, jobs=jobs, applications=applications)


@app.route("/admin-dashboard")
@role_required('admin')
def admin_dashboard():
    companies = get_users_by_role('company')
    students = get_users_by_role('student')
    all_jobs = get_all_jobs_admin()
    
    # Pre-resolve URLs for students
    for student in students:
        student['profile_pic'] = resolve_url_py(student.get('profile_pic'))
        student['resume_path'] = resolve_url_py(student.get('resume_path'))
        
    pending_companies = [c for c in companies if not c.get('is_verified')]
    pending_students = []
    pending_jobs = []
    
    return render_template("admin-dashboard.html", 
                         user=session['user'], 
                         pending_companies=pending_companies, 
                         all_companies=companies,
                         students=students,
                         pending_students=pending_students,
                         all_jobs=all_jobs,
                         pending_jobs=pending_jobs)

@app.route("/admin/delete-user/<uid>", methods=['POST'])
@role_required('admin')
def delete_user(uid):
    try:
        delete_user_db(uid)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/admin/verify-company/<uid>", methods=['POST'])
@role_required('admin')
def verify_company_route(uid):
    update_user_status(uid, {'is_verified': 1})
    return jsonify({'success': True})

@app.route("/admin/verify-student/<uid>", methods=['POST'])
@role_required('admin')
def verify_student_route(uid):
    update_user_status(uid, {'is_verified': 1})
    return jsonify({'success': True})

@app.route("/admin/unverify-student/<uid>", methods=['POST'])
@role_required('admin')
def unverify_student_route(uid):
    update_user_status(uid, {'is_verified': 0})
    return jsonify({'success': True})

@app.route("/admin/unverify-company/<uid>", methods=['POST'])
@role_required('admin')
def unverify_company_route(uid):
    update_user_status(uid, {'is_verified': 0})
    return jsonify({'success': True})

@app.route("/admin/edit-profile/<uid>", methods=['POST'])
@role_required('admin')
def admin_edit_profile(uid):
    data = request.json
    try:
        update_user_status(uid, data)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/admin/verify-job/<int:job_id>", methods=['POST'])
@role_required('admin')
def verify_job_route(job_id):
    update_job_verification(job_id, 1)
    return jsonify({'success': True})

@app.route("/admin/unverify-job/<int:job_id>", methods=['POST'])
@role_required('admin')
def unverify_job_route(job_id):
    update_job_verification(job_id, 0)
    return jsonify({'success': True})

@app.route("/admin/delete-job/<int:job_id>", methods=['POST'])
@role_required('admin')
def delete_job_route(job_id):
    try:
        delete_job_db(job_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/post-internship", methods=['GET', 'POST'])
@role_required('company')
def post_internship():
    if request.method == 'GET':
        return render_template("post-internship.html", user=session['user'])
    
    # Handle POST
    uid = session['user']['uid']
    user_data = get_user(uid)
    
    # Remove verification check for companies if needed, but user only asked for students and internships.
    # However, internships themselves no longer need verification.
    # Let's keep company verification for now as per plan focus.
    if not user_data.get('is_verified'):
        return render_template("post-internship.html", user=session['user'], error="Account not verified")

    job_data = {
        'title': request.form.get('title'),
        'mode': request.form.get('mode'),
        'location': request.form.get('location'),
        'duration': request.form.get('duration'),
        'stipend': request.form.get('stipend'),
        'skills_required': request.form.get('skills_required'),
        'description': request.form.get('description'),
        'posted_at': session.get('current_time', 'now') 
    }
    
    create_job(uid, job_data)
    return redirect(url_for('company_dashboard'))

@app.route("/post-job", methods=['POST'])
@role_required('company')
def post_job():
    uid = session['user']['uid']
    user_data = get_user(uid)
    
    if not user_data.get('is_verified'):
        return jsonify({'success': False, 'error': 'Account not verified'}), 403
        
    job_data = request.json
    create_job(uid, job_data)
    return jsonify({'success': True})

@app.route("/update-job/<int:job_id>", methods=['POST'])
@role_required('company')
def update_job_route(job_id):
    uid = session['user']['uid']
    # Verify ownership before updating
    from app.db import get_jobs, update_job
    all_jobs = get_jobs(uid)
    if not any(j['id'] == job_id for j in all_jobs):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    job_data = request.json
    update_job(job_id, job_data)
    return jsonify({'success': True})


@app.route("/apply-job", methods=['POST'])
@role_required('student')
def apply_job():
    uid = session['user']['uid']
    user_data = get_user(uid)
    
    # Calculate profile completion dynamically to ensure consistency
    is_profile_complete = False
    if user_data:
        is_profile_complete = all([
            user_data.get('branch'),
            user_data.get('skills'),
            user_data.get('enrollment_number')
        ])
    
    if not is_profile_complete:
        return jsonify({'success': False, 'error': 'Please complete your profile (Enrollment, Branch, Skills) before applying.'}), 400
        
    data = request.json
    job_id = data.get('job_id')
    
    # Custom application data (can be expanded)
    application_data = {
        'student_name': user_data.get('name'),
        'student_email': user_data.get('email'),
        'applied_at': session.get('current_time', 'now') # Placeholder or real time
    }
    
    from app.db import apply_for_job
    apply_for_job(job_id, uid, application_data)
    return jsonify({'success': True})

@app.route("/internship/<int:job_id>")
def internship_details(job_id):
    # Fetch job data
    job = get_job_by_id(job_id)
    if not job:
        return "Internship not found", 404
        
    user = session.get('user')
    applied = False
    application_status = None
    
    if user and user.get('role') == 'student':
        from app.db import get_applications
        student_apps = get_applications(student_uid=user['uid'])
        # Check if already applied
        matching_app = next((app for app in student_apps if app['job_id'] == job_id), None)
        if matching_app:
            applied = True
            application_status = matching_app['status']
            
    return render_template("internship-details.html", 
                           job=job, 
                           user=user, 
                           applied=applied,
                           application_status=application_status)

@app.route("/update-application-status", methods=['POST'])
@role_required('company')
def update_application_status():
    company_uid = session['user']['uid']
    data = request.json
    app_id = data.get('app_id')
    new_status = data.get('status')
    
    from app.db import get_applications, update_application_status_db
    # SECURITY: Verify the application belongs to a job posted by this company
    apps = get_applications(company_uid=company_uid)
    
    print(f"DEBUG: Company UID: {company_uid}")
    print(f"DEBUG: Requested App ID: {app_id} (Type: {type(app_id)})")
    print(f"DEBUG: Found Apps: {[a['id'] for a in apps]}")
    
    if not any(str(a['id']) == str(app_id) for a in apps):
        print("DEBUG: Authorization Failed")
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    update_application_status_db(app_id, new_status)
    
    # Send Notification to Student
    from app.db import create_notification
    # Find the application to get student UID and job details
    app_data = next((a for a in apps if str(a['id']) == str(app_id)), None)
    
    if app_data:
        student_uid = app_data['student_uid']
        job_title = app_data['job_info'].get('title', 'Internship')
        company_name = app_data['company_name']
        
        status_msg = new_status.replace('_', ' ').title()
        
        # Custom messages based on status
        if new_status == 'shortlisted':
            message = f"Congratulations! You have been SHORTLISTED for the {job_title} position at {company_name}. The company may contact you for further rounds."
        elif new_status == 'hired':
            message = f"You're Hired! Congratulations on securing the {job_title} role at {company_name}!"
        elif new_status == 'rejected':
            message = f"Update on your application for {job_title} at {company_name}. Unfortunately, you were not selected this time."
        else:
             message = f"Update: Your application for {job_title} at {company_name} is now {status_msg}."

        link = url_for('student_dashboard', section='applications')
        
        create_notification(student_uid, message, link)
        
    return jsonify({'success': True})

@app.route("/api/notifications")
@role_required('student')
def get_notifications_api():
    uid = session['user']['uid']
    from app.db import get_unread_notifications
    notifications = get_unread_notifications(uid)
    return jsonify(notifications)

@app.route("/api/notifications/mark-read/<int:notif_id>", methods=['POST'])
@role_required('student')
def mark_read_api(notif_id):
    from app.db import mark_notification_read
    # Verification could be added here to ensure ownership
    mark_notification_read(notif_id)
    return jsonify({'success': True})

@app.route("/api/notifications/mark-all-read", methods=['POST'])
@role_required('student')
def mark_all_read_api():
    uid = session['user']['uid']
    from app.db import mark_all_notifications_read
    mark_all_notifications_read(uid)
    return jsonify({'success': True})


@app.route("/withdraw-application", methods=['POST'])
@role_required('student')
def withdraw_application():
    student_uid = session['user']['uid']
    data = request.json
    app_id = data.get('app_id')
    
    from app.db import get_applications, update_application_status_db
    
    # SECURITY: Verify the application belongs to this student
    apps = get_applications(student_uid=student_uid)
    if not any(str(a['id']) == str(app_id) for a in apps):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Only allow withdrawing pending applications
    app = next((a for a in apps if str(a['id']) == str(app_id)), None)
    if app and app['status'] != 'pending':
        return jsonify({'success': False, 'error': 'Cannot withdraw processed application'}), 400
        
    update_application_status_db(app_id, 'withdrawn')
    return jsonify({'success': True})

# Helper function to get verified companies
def get_verified_companies():
    all_companies = get_users_by_role('company')
    return [c for c in all_companies if c.get('is_verified')]

# Helper function to get company profile (including verification check)
def get_company_profile(uid):
    company_data = get_user(uid)
    if not company_data or company_data.get('role') != 'company' or not company_data.get('is_verified'):
        return None
    return company_data

@app.route("/explore-companies")
def explore_companies():
    companies = get_verified_companies()
    user = session.get('user')
    return render_template('explore-companies.html', companies=companies, user=user)

@app.route("/company-profile/<uid>")
def company_profile_view(uid):
    company = get_company_profile(uid)
    if not company:
        return "Company not found or not verified", 404
        
    user = session.get('user')
    can_apply = user and user.get('role') == 'student'
    
    # Track which jobs the student has already applied for and their status
    applied_jobs = {}
    if can_apply:
        from app.db import get_applications
        student_apps = get_applications(student_uid=user['uid'])
        applied_jobs = {str(app['job_id']): app['status'] for app in student_apps}
    
    jobs = get_jobs(uid)
    
    return render_template("company-profile.html", 
                           company=company, 
                           user=user,
                           can_apply=can_apply,
                           jobs=jobs,
                           applied_jobs=applied_jobs)

@app.route("/update-company-profile", methods=['POST'])
@role_required('company')
def update_company_profile():
    uid = session['user']['uid']
    profile_data = request.json
    
    # Update SQLite - directly targeting employer table to avoid role detection issues
    from app.db import upsert_employer
    upsert_employer(uid, profile_data)
    
    # Update session name if it changed
    if 'name' in profile_data:
        session['user']['name'] = profile_data['name']
        session.modified = True
        
    return jsonify({'success': True})

@app.route("/student-profile/<uid>")
def student_profile_public(uid):
    # SECURITY: Only Companies and Admin can view full student profiles
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session['user'].get('role')
    if role not in ['company', 'admin']:
        return render_template("unauthorized.html"), 403
    
    student = get_user(uid) # This fetches from students table
    
    if not student:
        return "Student not found", 404
        
    # Check for application context
    app_id = request.args.get('app_id')
    application = None
    
    if app_id:
        from app.db import get_applications
        # Verify this application exists and relates to this company
        if role == 'company':
            company_uid = session['user']['uid']
            apps = get_applications(company_uid=company_uid)
            # Find specific app
            application = next((a for a in apps if str(a['id']) == str(app_id)), None)
            
            # Security check: Ensure app belongs to this student
            if application and application['student_uid'] != uid:
                application = None # Mismatch, don't show actions
        elif role == 'admin':
            # Admin can see whatever, but for now let's just fetch it
            pass # Implement if needed for admin to override status
            
    return render_template("student-profile-public.html", student=student, application=application)

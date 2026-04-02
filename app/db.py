import sqlite3
import json
import os

DB_NAME = "kairva_ld.db"
# Vercel provides POSTGRES_URL, POSTGRES_URL_NON_POOLING, or SUPABASE_POSTGRES_URL by default
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('POSTGRES_URL_NON_POOLING') or os.environ.get('SUPABASE_POSTGRES_URL')
IS_POSTGRES = DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://'))
PLACEHOLDER = '%s' if IS_POSTGRES else '?'

def get_db_connection():
    """Get a database connection (PostgreSQL or SQLite)"""
    if IS_POSTGRES:
        url_preview = DATABASE_URL[:20] if DATABASE_URL else "None"
        print(f"Attempting to connect to PostgreSQL... URL starts with: {url_preview}...")
        import psycopg2
        from psycopg2.extras import RealDictCursor
        # Fix the 'postgres://' vs 'postgresql://' issue if necessary
        url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        try:
            conn = psycopg2.connect(url, connect_timeout=5)
            print("Successfully connected to PostgreSQL")
            return conn
        except Exception as e:
            print(f"DATABASE CONNECTION ERROR: {e}")
            raise e
    else:
        print(f"Using local SQLite database: {DB_NAME}")
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def get_cursor(conn):
    """Get a cursor (RealDictCursor for Postgres, standard for SQLite)"""
    if IS_POSTGRES:
        from psycopg2.extras import RealDictCursor
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Type mapping for Postgres vs SQLite
    serial_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_type = "TEXT"
    timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    bool_type = "INTEGER"  # Forced to INTEGER to match user's Postgres schema and avoid mismatch errors
    
    # Create students table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS students (
            uid {text_type} PRIMARY KEY,
            name {text_type} NOT NULL,
            email {text_type} NOT NULL UNIQUE,
            enrollment_number {text_type},
            branch {text_type},
            admission_year INTEGER,
            passout_year INTEGER,
            study_type {text_type},
           cpi REAL,
            skills {text_type},
            linkedin_url {text_type},
            github_url {text_type},
            portfolio_url {text_type},
            resume_path {text_type},
            profile_pic {text_type},
            is_verified {bool_type} DEFAULT 1,
            created_at {timestamp_type}
        )
    ''')

    # Create employers table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS employers (
            uid {text_type} PRIMARY KEY,
            name {text_type} NOT NULL,
            email {text_type} NOT NULL UNIQUE,
            company_description {text_type},
            industry {text_type},
            website {text_type},
            year_founded INTEGER,
            location {text_type},
            size {text_type},
            culture {text_type},
            is_verified {bool_type} DEFAULT 0,
            created_at {timestamp_type}
        )
    ''')
    
    # Create table for jobs
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS jobs (
            id {serial_type},
            company_uid {text_type},
            data {text_type},
            is_verified {bool_type} DEFAULT 1,
            FOREIGN KEY(company_uid) REFERENCES employers(uid)
        )
    ''')
    
    # Create table for applications
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS applications (
            id {serial_type},
            job_id INTEGER,
            student_uid {text_type},
            status {text_type} DEFAULT 'pending',
            data {text_type},
            FOREIGN KEY(job_id) REFERENCES jobs(id),
            FOREIGN KEY(student_uid) REFERENCES students(uid)
        )
    ''')
    
    # Create table for notifications
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS notifications (
            id {serial_type},
            user_uid {text_type},
            message {text_type},
            link {text_type},
            is_read {bool_type} DEFAULT 0,
            created_at {timestamp_type},
            FOREIGN KEY(user_uid) REFERENCES students(uid)
        )
    ''')
    
    conn.commit()
    conn.close()


# ==================== Student Functions ====================

def get_student(uid):
    """Get student by UID"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute(f"""
        SELECT * 
        FROM students 
        WHERE uid={PLACEHOLDER}
    """, (uid,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def upsert_student(uid, student_data):
    """Insert or update student record - role-aware and schema-safe"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get table columns to filter input data
    if IS_POSTGRES:
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'students'")
        columns = [row[0] for row in c.fetchall()]
    else:
        c.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in c.fetchall()]
        
    clean_data = {k: v for k, v in student_data.items() if k in columns and k != 'uid'}
    
    # Normalize boolean fields to integers for Postgres compatibility
    if 'is_verified' in clean_data:
        clean_data['is_verified'] = 1 if clean_data['is_verified'] else 0
    
    # Check if student exists
    c.execute(f"SELECT uid FROM students WHERE uid={PLACEHOLDER}", (uid,))
    exists = c.fetchone()
    
    if exists:
        if clean_data:
            set_clause = ', '.join([f"{key}={PLACEHOLDER}" for key in clean_data.keys()])
            values = list(clean_data.values()) + [uid]
            c.execute(f"UPDATE students SET {set_clause} WHERE uid={PLACEHOLDER}", values)
    else:
        # Insert new student
        clean_data['uid'] = uid
        cols = ', '.join(clean_data.keys())
        placeholders = ', '.join([PLACEHOLDER for _ in clean_data])
        c.execute(f"INSERT INTO students ({cols}) VALUES ({placeholders})", list(clean_data.values()))
    
    conn.commit()
    conn.close()

def get_all_students():
    """Get all students"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute("SELECT * FROM students")
    results = c.fetchall()
    conn.close()
    return [dict(row) for row in results]

def update_student_verification(uid, is_verified):
    """Update student verification status"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE students SET is_verified={PLACEHOLDER} WHERE uid={PLACEHOLDER}", (int(is_verified), uid))
    conn.commit()
    conn.close()


# ==================== Employer Functions ====================

def get_employer(uid):
    """Get employer by UID"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute(f"SELECT * FROM employers WHERE uid={PLACEHOLDER}", (uid,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def upsert_employer(uid, employer_data):
    """Insert or update employer record - role-aware and schema-safe"""
    conn = get_db_connection()
    c = conn.cursor()
    
    if IS_POSTGRES:
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'employers'")
        columns = [row[0] for row in c.fetchall()]
    else:
        c.execute("PRAGMA table_info(employers)")
        columns = [row[1] for row in c.fetchall()]
        
    clean_data = {k: v for k, v in employer_data.items() if k in columns and k != 'uid'}
    
    # Normalize boolean fields to integers for Postgres compatibility
    if 'is_verified' in clean_data:
        clean_data['is_verified'] = 1 if clean_data['is_verified'] else 0
    
    c.execute(f"SELECT uid FROM employers WHERE uid={PLACEHOLDER}", (uid,))
    exists = c.fetchone()
    
    if exists:
        if clean_data:
            set_clause = ', '.join([f"{key}={PLACEHOLDER}" for key in clean_data.keys()])
            values = list(clean_data.values()) + [uid]
            c.execute(f"UPDATE employers SET {set_clause} WHERE uid={PLACEHOLDER}", values)
    else:
        clean_data['uid'] = uid
        cols = ', '.join(clean_data.keys())
        placeholders = ', '.join([PLACEHOLDER for _ in clean_data])
        c.execute(f"INSERT INTO employers ({cols}) VALUES ({placeholders})", list(clean_data.values()))
    
    conn.commit()
    conn.close()

def get_all_employers():
    """Get all employers"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute("SELECT * FROM employers")
    results = c.fetchall()
    conn.close()
    return [dict(row) for row in results]

def update_employer_verification(uid, is_verified):
    """Update employer verification status"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE employers SET is_verified={PLACEHOLDER} WHERE uid={PLACEHOLDER}", (int(is_verified), uid))
    conn.commit()
    conn.close()




# ==================== Generic User Functions (for backward compatibility) ====================

def get_user(uid, role=None):
    """Get user by UID - backwards compatible wrapper"""
    if role == 'student':
        return get_student(uid)
    elif role == 'company':
        return get_employer(uid)
    else:
        # Try all tables
        user = get_student(uid)
        if user:
            user['role'] = 'student'
            return user
        user = get_employer(uid)
        if user:
            user['role'] = 'company'
            return user
        return None

def upsert_user(uid, user_data):
    """Insert or update user - backwards compatible wrapper"""
    role = user_data.get('role', 'student')
    
    if role == 'student':
        upsert_student(uid, user_data)
    elif role == 'company':
        upsert_employer(uid, user_data)

def get_users_by_role(role):
    """Get all users by role - backwards compatible"""
    if role == 'student':
        users = get_all_students()
        for user in users:
            user['role'] = 'student'
        return users
    elif role == 'company':
        users = get_all_employers()
        for user in users:
            user['role'] = 'company'
        return users
    return []

def update_user_status(uid, status_dict):
    """Update specific fields - backwards compatible"""
    # Determine which table by checking all
    if get_student(uid):
        upsert_student(uid, status_dict)
    elif get_employer(uid):
        upsert_employer(uid, status_dict)


# ==================== Job Functions ====================

# ==================== Job Functions ====================

def create_job(company_uid, job_data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"INSERT INTO jobs (company_uid, data) VALUES ({PLACEHOLDER}, {PLACEHOLDER})", (company_uid, json.dumps(job_data)))
    conn.commit()
    conn.close()

def update_job(job_id, job_data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE jobs SET data={PLACEHOLDER} WHERE id={PLACEHOLDER}", (json.dumps(job_data), job_id))
    conn.commit()
    conn.close()

def get_jobs(company_uid=None):
    conn = get_db_connection()
    c = get_cursor(conn)
    
    query = f"""
        SELECT j.id, j.company_uid, j.data, e.name as company_name, j.is_verified,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) as app_count
        FROM jobs j
        JOIN employers e ON j.company_uid = e.uid
    """
    params = []
    
    if company_uid:
        query += f" WHERE j.company_uid={PLACEHOLDER}"
        params.append(company_uid)
        
    c.execute(query, params)
    
    jobs = []
    for row in c.fetchall():
        job_data = json.loads(row['data'])
        job_data['id'] = row['id']
        job_data['company_uid'] = row['company_uid']
        job_data['company_name'] = row['company_name']
        job_data['is_verified'] = row['is_verified']
        job_data['app_count'] = row['app_count']
        
        jobs.append(job_data)
    conn.close()
    return jobs

def get_job_by_id(job_id):
    """Get a single job by ID with company details"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute(f"""
        SELECT j.id, j.company_uid, j.data, e.name as company_name, j.is_verified,
               e.company_description, e.industry, e.website
        FROM jobs j
        JOIN employers e ON j.company_uid = e.uid
        WHERE j.id={PLACEHOLDER}
    """, (job_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        job_data = json.loads(row['data'])
        job_data['id'] = row['id']
        job_data['company_uid'] = row['company_uid']
        job_data['company_name'] = row['company_name']
        job_data['is_verified'] = row['is_verified']
        job_data['company_description'] = row['company_description']
        job_data['company_industry'] = row['industry']
        job_data['company_website'] = row['website']
        return job_data
    return None

def get_all_jobs_admin():
    """Get all jobs with company name and verification status for admin"""
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute("""
        SELECT j.id, j.company_uid, j.data, j.is_verified, e.name as company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) as app_count
        FROM jobs j
        JOIN employers e ON j.company_uid = e.uid
    """)
    rows = c.fetchall()
    conn.close()
    
    jobs = []
    for row in rows:
        job = json.loads(row['data'])
        job['id'] = row['id']
        job['company_uid'] = row['company_uid']
        job['company_name'] = row['company_name']
        job['is_verified'] = row['is_verified']
        job['app_count'] = row['app_count']
        
        jobs.append(job)
    return jobs

def update_job_verification(job_id, is_verified):
    """Update job verification status"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE jobs SET is_verified={PLACEHOLDER} WHERE id={PLACEHOLDER}", (int(is_verified), job_id))
    conn.commit()
    conn.close()

def delete_job_db(job_id):
    """Delete a job and its applications"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"DELETE FROM applications WHERE job_id={PLACEHOLDER}", (job_id,))
    c.execute(f"DELETE FROM jobs WHERE id={PLACEHOLDER}", (job_id,))
    conn.commit()
    conn.close()


# ==================== Application Functions ====================

def apply_for_job(job_id, student_uid, application_data):
    from datetime import datetime
    application_data['applied_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check for existing application (including withdrawn ones)
    c.execute(f"SELECT id, status FROM applications WHERE job_id={PLACEHOLDER} AND student_uid={PLACEHOLDER}", (job_id, student_uid))
    existing = c.fetchone()
    
    if existing:
        if IS_POSTGRES:
            # Postgres fetchone with cursor result is a list/dict
            app_id = existing[0] if isinstance(existing, (list, tuple)) else existing['id']
            status = existing[1] if isinstance(existing, (list, tuple)) else existing['status']
        else:
            app_id, status = existing
            
        if status == 'withdrawn':
            # Reactivate application if it was withdrawn
            c.execute(f"UPDATE applications SET status='pending', data={PLACEHOLDER} WHERE id={PLACEHOLDER}", 
                      (json.dumps(application_data), app_id))
        else:
            # Already has an active application, don't create duplicate
            conn.close()
            return False # Indicate no new record created
    else:
        # Create new application
        c.execute(f"INSERT INTO applications (job_id, student_uid, data) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})", 
                  (job_id, student_uid, json.dumps(application_data)))
    
    conn.commit()
    conn.close()
    return True

def get_applications(job_id=None, company_uid=None, student_uid=None):
    conn = get_db_connection()
    c = get_cursor(conn)
    
    query = """
        SELECT a.id, a.job_id, a.student_uid, a.status, a.data, 
               j.data as job_data, s.name as student_name, s.email as student_email,
               s.branch as student_branch, s.cpi as student_cpi, s.skills as student_skills,
               s.passout_year as student_passout, e.name as company_name, s.profile_pic,
               s.linkedin_url, s.github_url, s.portfolio_url, s.resume_path,
               s.enrollment_number, s.admission_year, s.study_type
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id
        JOIN students s ON a.student_uid = s.uid
        JOIN employers e ON j.company_uid = e.uid
    """
    params = []
    
    first_filter = True
    if job_id:
        query += f" WHERE a.job_id={PLACEHOLDER}"
        params.append(job_id)
        first_filter = False
    
    if company_uid:
        query += (" WHERE " if first_filter else " AND ") + f"j.company_uid={PLACEHOLDER}"
        params.append(company_uid)
        first_filter = False
        
    if student_uid:
        query += (" WHERE " if first_filter else " AND ") + f"a.student_uid={PLACEHOLDER}"
        params.append(student_uid)
        
    c.execute(query, params)
    
    apps = []
    for row in c.fetchall():
        app_data = json.loads(row['data'])
        app_data['id'] = row['id']
        app_data['job_id'] = row['job_id']
        app_data['student_uid'] = row['student_uid']
        app_data['status'] = row['status']
        app_data['job_info'] = json.loads(row['job_data'])
        app_data['student_name'] = row['student_name']
        app_data['student_email'] = row['student_email']
        app_data['student_branch'] = row['student_branch']
        app_data['student_cpi'] = row['student_cpi']
        app_data['student_skills'] = row['student_skills']
        app_data['student_passout'] = row['student_passout']
        app_data['company_name'] = row['company_name']
        app_data['profile_pic'] = row['profile_pic']
        
        # New fields
        app_data['linkedin_url'] = row['linkedin_url']
        app_data['github_url'] = row['github_url']
        app_data['portfolio_url'] = row['portfolio_url']
        app_data['resume_path'] = row['resume_path']
        app_data['student_enrollment'] = row['enrollment_number']
        app_data['student_admission'] = row['admission_year']
        app_data['student_study_type'] = row['study_type']
        
        apps.append(app_data)
    conn.close()
    return apps

def update_application_status_db(app_id, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE applications SET status={PLACEHOLDER} WHERE id={PLACEHOLDER}", (status, app_id))
    conn.commit()
    conn.close()

def delete_user_db(uid):
    """Permanently delete a user and their associated data"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Determine which table the user is in
    if get_student(uid):
        # Delete applications made by the student
        c.execute(f"DELETE FROM applications WHERE student_uid={PLACEHOLDER}", (uid,))
        c.execute(f"DELETE FROM students WHERE uid={PLACEHOLDER}", (uid,))
    elif get_employer(uid):
        # Delete applications for jobs posted by the company
        c.execute(f"DELETE FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE company_uid={PLACEHOLDER})", (uid,))
        # Delete jobs posted by the company
        c.execute(f"DELETE FROM jobs WHERE company_uid={PLACEHOLDER}", (uid,))
        c.execute(f"DELETE FROM employers WHERE uid={PLACEHOLDER}", (uid,))
    
    conn.commit()
    conn.close()

# ==================== Analytics Functions ====================

def get_market_insights(student_uid=None):
    """Calculate real market insights from existing data"""
    conn = get_db_connection()
    c = get_cursor(conn)
    
    c.execute("SELECT data FROM jobs")
    all_jobs = c.fetchall()

    # 1. Trending Industry
    c.execute("""
        SELECT e.industry, COUNT(j.id) as count
        FROM jobs j
        JOIN employers e ON j.company_uid = e.uid
        WHERE e.industry IS NOT NULL AND e.industry != ''
        GROUP BY e.industry
        ORDER BY count DESC
        LIMIT 1
    """)
    industry_row = c.fetchone()
    trending_industry = industry_row['industry'] if industry_row else "Technology"

    # 2. Acceptance Probability (Skill Match)
    prob = 0
    if student_uid:
        c.execute(f"SELECT skills FROM students WHERE uid={PLACEHOLDER}", (student_uid,))
        student_row = c.fetchone()
        if student_row and student_row['skills']:
            s_skills = set([s.strip().lower() for s in student_row['skills'].split(',')])
            
            total_matches = 0
            job_count = 0
            for row in all_jobs:
                job_data = json.loads(row['data'])
                j_skills = set([s.strip().lower() for s in job_data.get('skills_required', '').split(',')])
                if j_skills:
                    overlap = len(s_skills.intersection(j_skills)) / len(j_skills)
                    total_matches += overlap
                    job_count += 1
            
            if job_count > 0:
                prob = int((total_matches / job_count) * 100 + 20) # Add a base 20% floor for general profile
                prob = min(95, prob) # Cap at 95%
    else:
        prob = 45 # Default for new users

    conn.close()
    
    return {
        "trending_industry": trending_industry,
        "acceptance_prob": prob,
        "total_listings": len(all_jobs)
    }

# ==================== Notification Functions ====================

def create_notification(user_uid, message, link=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"INSERT INTO notifications (user_uid, message, link) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})", 
              (user_uid, message, link))
    conn.commit()
    conn.close()

def get_unread_notifications(user_uid):
    conn = get_db_connection()
    c = get_cursor(conn)
    c.execute(f"SELECT * FROM notifications WHERE user_uid={PLACEHOLDER} AND is_read=0 ORDER BY created_at DESC", (user_uid,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_notification_read(notification_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE notifications SET is_read=1 WHERE id={PLACEHOLDER}", (notification_id,))
    conn.commit()
    conn.close()

def mark_all_notifications_read(user_uid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE notifications SET is_read=1 WHERE user_uid={PLACEHOLDER}", (user_uid,))
    conn.commit()
    conn.close()

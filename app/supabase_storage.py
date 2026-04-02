import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"FAILED TO INITIALIZE SUPABASE CLIENT: {e}")

# Single bucket for all student data
BUCKET = 'student-data'

# Signed URL expiry in seconds (1 hour)
SIGNED_URL_EXPIRY = 3600


def validate_file(filename, file_data, allowed_extensions=None):
    """Securely validate file extension and size.
    
    Args:
        filename: Name of the file
        file_data: Bytes of the file
        allowed_extensions: Set of allowed extensions (e.g. {'pdf', 'png'})
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not filename:
        return False, "No filename provided."
    
    # 1. Check Extension
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if allowed_extensions and ext not in allowed_extensions:
        return False, f"Extension '.{ext}' is not allowed. Supported: {', '.join(allowed_extensions)}"
    
    # 2. Check Size (Hard limit of 10MB)
    MAX_SIZE = 10 * 1024 * 1024
    if len(file_data) > MAX_SIZE:
        return False, "File is too large. Maximum size allowed is 10MB."
    
    return True, None

def upload_resume(uid, file_data, original_filename):
    """Upload a resume PDF to Supabase Storage (private bucket)."""
    # Use centralized validation (called from routes too, but as a secondary check)
    is_valid, error = validate_file(original_filename, file_data, {'pdf'})
    if not is_valid:
        raise ValueError(error)

    from werkzeug.utils import secure_filename
    filename = secure_filename(f"{uid}_{original_filename}")
    file_path = f"resumes/{uid}/{filename}"
    
    # Upload with upsert
    supabase.storage.from_(BUCKET).upload(
        file_path,
        file_data,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )
    
    return f"supabase://{BUCKET}/{file_path}"


def upload_profile_pic(uid, file_data, original_filename):
    """Upload a profile picture to Supabase Storage (private bucket)."""
    allowed = {'png', 'jpg', 'jpeg'}
    is_valid, error = validate_file(original_filename, file_data, allowed)
    if not is_valid:
        raise ValueError(error)

    from werkzeug.utils import secure_filename
    import os as _os
    
    file_ext = _os.path.splitext(original_filename)[1].lower()
    filename = secure_filename(f"{uid}_profile{file_ext}")
    file_path = f"profile-pics/{uid}/{filename}"
    
    # Determine content type
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
    }
    content_type = content_types.get(file_ext, 'image/jpeg')
    
    # Upload with upsert
    supabase.storage.from_(BUCKET).upload(
        file_path,
        file_data,
        file_options={"content-type": content_type, "upsert": "true"}
    )
    
    return f"supabase://{BUCKET}/{file_path}"


def get_signed_url(storage_path):
    """Generate a temporary signed URL for a private file.
    
    Args:
        storage_path: Path in format 'supabase://bucket/path/to/file'
    
    Returns:
        Signed URL string valid for SIGNED_URL_EXPIRY seconds, or None on error
    """
    if not storage_path or not storage_path.startswith('supabase://'):
        return None
    
    try:
        # Parse: supabase://bucket-name/path/to/file
        path_part = storage_path.replace('supabase://', '')
        bucket = path_part.split('/')[0]
        file_path = '/'.join(path_part.split('/')[1:])
        
        result = supabase.storage.from_(bucket).create_signed_url(
            file_path, SIGNED_URL_EXPIRY
        )
        return result.get('signedURL') or result.get('signedUrl')
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        return None


def delete_file(storage_path):
    """Delete a file from Supabase Storage.
    
    Args:
        storage_path: Path in format 'supabase://bucket/path/to/file'
    """
    if not storage_path or not storage_path.startswith('supabase://'):
        return False
    
    try:
        path_part = storage_path.replace('supabase://', '')
        bucket = path_part.split('/')[0]
        file_path = '/'.join(path_part.split('/')[1:])
        
        supabase.storage.from_(bucket).remove([file_path])
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False

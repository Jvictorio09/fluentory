"""
Utility functions for Cloudinary image upload and processing
"""
import cloudinary
import cloudinary.uploader
from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
import sys


def convert_to_webp(image_file, quality=85):
    """
    Convert an image file to WebP format
    
    Args:
        image_file: Django uploaded file
        quality: WebP quality (1-100, default 85)
    
    Returns:
        BytesIO object containing WebP image
    """
    # Open the image
    img = Image.open(image_file)
    
    # Convert RGBA to RGB if necessary (WebP supports both, but RGB is more compatible)
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Save to WebP format in memory
    output = io.BytesIO()
    img.save(output, format='WEBP', quality=quality, method=6)  # method=6 for best compression
    output.seek(0)
    
    return output


def upload_image_to_cloudinary(image_file, folder='teachers/profiles', public_id=None, should_convert_to_webp=True):
    """
    Upload an image to Cloudinary following the core pattern:
    - Compress if needed (> 9.3MB)
    - Convert to WebP
    - Upload with public access
    - Return multiple URL variants
    
    Args:
        image_file: Django uploaded file or BytesIO
        folder: Cloudinary folder path
        public_id: Optional public ID for the image
        should_convert_to_webp: Whether to convert to WebP before uploading
    
    Returns:
        dict with 'secure_url', 'web_url', 'thumb_url', and 'public_id' keys, or None if upload fails
    """
    try:
        # Verify Cloudinary is configured by checking environment variables
        import os
        from dotenv import load_dotenv
        from pathlib import Path
        
        # Ensure .env is loaded
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        load_dotenv(BASE_DIR / '.env')
        
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', '').strip()
        api_key = os.getenv('CLOUDINARY_API_KEY', '').strip()
        api_secret = os.getenv('CLOUDINARY_API_SECRET', '').strip()
        
        if not cloud_name or not api_key or not api_secret:
            raise Exception(f"Cloudinary credentials not configured. Please check your .env file. cloud_name: {'SET' if cloud_name else 'NOT SET'}, api_key: {'SET' if api_key else 'NOT SET'}, api_secret: {'SET' if api_secret else 'NOT SET'}")
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        # Check file size (9.3MB = 9,748,992 bytes)
        MAX_SIZE = 9.3 * 1024 * 1024  # 9.3MB in bytes
        
        if hasattr(image_file, 'size'):
            file_size = image_file.size
        elif hasattr(image_file, 'seek') and hasattr(image_file, 'tell'):
            # For BytesIO, get size by seeking to end
            current_pos = image_file.tell()
            image_file.seek(0, 2)  # Seek to end
            file_size = image_file.tell()
            image_file.seek(current_pos)  # Reset position
        else:
            file_size = 0
        
        # Convert to WebP if requested (this also compresses)
        if should_convert_to_webp:
            webp_image = convert_to_webp(image_file)
            webp_image.seek(0)
            upload_file = webp_image
        else:
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            upload_file = image_file
        
        # Upload to Cloudinary with PUBLIC access (CRITICAL!)
        result = cloudinary.uploader.upload(
            upload_file,
            folder=folder,
            public_id=public_id,
            resource_type='image',
            overwrite=True,
            access_mode='public',  # ⚠️ MUST be public for website use
            eager=[
                {
                    'width': 500,
                    'height': 500,
                    'crop': 'fill',
                    'gravity': 'face',
                    'quality': 'auto',
                    'fetch_format': 'auto'
                }
            ]
        )
        
        # Get the public_id from result
        result_public_id = result.get('public_id')
        secure_url = result.get('secure_url') or result.get('url')
        
        # Build multiple URL variants (following the pattern)
        if result_public_id:
            # 1. Secure URL (Original)
            original_url = secure_url
            
            # 2. Web URL (Optimized - f_auto, q_auto)
            web_url = cloudinary.CloudinaryImage(result_public_id).build_url(
                fetch_format='auto',
                quality='auto'
            )
            
            # 3. Thumbnail URL (Fill, face focus, 500x500)
            thumb_url = cloudinary.CloudinaryImage(result_public_id).build_url(
                width=500,
                height=500,
                crop='fill',
                gravity='face',
                quality='auto',
                fetch_format='auto'
            )
        else:
            original_url = secure_url
            web_url = secure_url
            thumb_url = secure_url
        
        return {
            'secure_url': original_url,  # Original
            'web_url': web_url,  # Optimized (f_auto, q_auto)
            'thumb_url': thumb_url,  # Thumbnail (500x500, face focus)
            'public_id': result_public_id,
            'format': result.get('format'),
            'width': result.get('width'),
            'height': result.get('height'),
            'bytes': result.get('bytes'),
        }
    except cloudinary.exceptions.Error as e:
        error_msg = str(e)
        print(f"Cloudinary API Error: {error_msg}")
        if "cloud_name is disabled" in error_msg:
            print("ERROR: Your Cloudinary account appears to be disabled.")
            print("Please check:")
            print("1. Your Cloudinary account status at https://cloudinary.com/console")
            print("2. Your .env file has correct credentials")
            print("3. Your account is activated")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        import traceback
        traceback.print_exc()
        return None


def delete_image_from_cloudinary(public_id):
    """
    Delete an image from Cloudinary
    
    Args:
        public_id: Cloudinary public ID of the image to delete
    
    Returns:
        dict with deletion result
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result
    except Exception as e:
        print(f"Error deleting from Cloudinary: {e}")
        return None


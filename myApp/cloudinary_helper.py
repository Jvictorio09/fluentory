"""
Cloudinary helper functions for image management
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
import os


def upload_image_from_url(image_url, folder='media', public_id=None):
    """
    Upload an image to Cloudinary from a URL
    
    Args:
        image_url: URL of the image to upload
        folder: Cloudinary folder path
        public_id: Optional custom public_id for the image
    
    Returns:
        dict with upload result including 'url', 'secure_url', 'public_id', etc.
    """
    try:
        result = cloudinary.uploader.upload(
            image_url,
            folder=folder,
            public_id=public_id,
            resource_type='image',
            overwrite=True
        )
        return {
            'success': True,
            'url': result.get('url'),
            'secure_url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'width': result.get('width'),
            'height': result.get('height'),
            'format': result.get('format'),
            'bytes': result.get('bytes'),
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def upload_image_from_file(file, folder='media', public_id=None):
    """
    Upload an image file to Cloudinary
    
    Args:
        file: Django UploadedFile object
        folder: Cloudinary folder path
        public_id: Optional custom public_id for the image
    
    Returns:
        dict with upload result
    """
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            public_id=public_id,
            resource_type='image',
            overwrite=True
        )
        return {
            'success': True,
            'url': result.get('url'),
            'secure_url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'width': result.get('width'),
            'height': result.get('height'),
            'format': result.get('format'),
            'bytes': result.get('bytes'),
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def delete_image(public_id):
    """
    Delete an image from Cloudinary
    
    Args:
        public_id: Cloudinary public_id of the image to delete
    
    Returns:
        dict with deletion result
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type='image')
        return {
            'success': result.get('result') == 'ok',
            'result': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_cloudinary_url(public_id, transformation=None):
    """
    Generate a Cloudinary URL with optional transformations
    
    Args:
        public_id: Cloudinary public_id
        transformation: dict of transformation options
    
    Returns:
        Cloudinary URL string
    """
    if transformation:
        return cloudinary.CloudinaryImage(public_id).build_url(**transformation)
    return cloudinary.CloudinaryImage(public_id).build_url()


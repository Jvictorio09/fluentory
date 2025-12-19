# Cloudinary Setup Guide

This guide will help you set up Cloudinary for image management in your Fluentory application.

## Step 1: Create a Cloudinary Account

1. Go to [https://cloudinary.com/users/register/free](https://cloudinary.com/users/register/free)
2. Sign up for a free account (includes 25GB storage and 25GB bandwidth per month)
3. Verify your email address

## Step 2: Get Your Cloudinary Credentials

1. After logging in, go to your [Dashboard](https://cloudinary.com/console)
2. You'll see your **Cloud Name**, **API Key**, and **API Secret**
3. Copy these three values - you'll need them in the next step

## Step 3: Add Credentials to Your .env File

Create or update your `.env` file in the project root with the following:

```env
# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

**Important:** Never commit your `.env` file to version control! It contains sensitive credentials.

## Step 4: Verify Installation

The Cloudinary packages are already installed:
- `cloudinary==1.43.0` - Python SDK
- `django-cloudinary-storage==0.3.0` - Django integration

## Step 5: How to Use

### Option 1: Upload Files Directly (Recommended)

1. Go to `/admin/media/add/` in your dashboard
2. Click "Upload File" tab
3. Select an image file from your computer
4. Fill in the details (title, description, etc.)
5. Click "Upload Media"
6. The file will automatically be uploaded to Cloudinary!

### Option 2: Use Existing Cloudinary URLs

1. Go to `/admin/media/add/` in your dashboard
2. Click "From Cloudinary URL" tab
3. Paste a Cloudinary URL (e.g., `https://res.cloudinary.com/your-cloud/image/upload/v1234567890/image.jpg`)
4. Fill in the details
5. Click "Upload Media"
6. The image will be copied to your Cloudinary account

### Option 3: Upload via Cloudinary Console

1. Go to [Cloudinary Console](https://cloudinary.com/console)
2. Click "Media Library" → "Upload"
3. Upload your images
4. Copy the image URL
5. Use Option 2 above to add it to your media library

## Managing Images in Admin Dashboard

### Site Images
- Go to `/admin/site-images/`
- Upload images for each landing page section:
  - Hero background
  - How It Works section
  - AI Tutor section
  - Certificates section
  - Pricing section
  - FAQ video thumbnail

### Media Library
- Go to `/admin/media/`
- View all uploaded images
- Edit, delete, or organize by category
- Search and filter images

## Cloudinary Features You Get

✅ **Automatic Image Optimization**
- Images are automatically optimized for web delivery
- Multiple format support (WebP, AVIF, etc.)

✅ **Transformations on the Fly**
- Resize, crop, rotate images via URL parameters
- Example: `?w=800&h=600&c=fill` for 800x600 fill crop

✅ **CDN Delivery**
- Images are served from Cloudinary's global CDN
- Fast loading times worldwide

✅ **Secure URLs**
- All images use HTTPS
- Optional signed URLs for private images

## Troubleshooting

### "Invalid Cloudinary credentials" error
- Check that your `.env` file has all three credentials
- Make sure there are no extra spaces or quotes
- Restart your Django server after updating `.env`

### Images not uploading
- Check your internet connection
- Verify Cloudinary account is active
- Check Django server logs for error messages

### Images not displaying
- Ensure `CLOUDINARY_CLOUD_NAME` is set correctly
- Check that images are public in Cloudinary (or use signed URLs)
- Verify the image URLs in your templates

## Need Help?

- [Cloudinary Documentation](https://cloudinary.com/documentation)
- [Django Cloudinary Storage Docs](https://github.com/klis87/django-cloudinary-storage)
- Check your Cloudinary dashboard for usage statistics and settings


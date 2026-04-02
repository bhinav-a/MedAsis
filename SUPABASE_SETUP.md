# Supabase Authentication Setup Guide

This guide will help you set up Supabase authentication for MedAsis.

## Step 1: Create a Supabase Project

1. Go to [Supabase](https://supabase.com)
2. Click **"Sign In"** or **"Start Your Project"** 
3. Sign up with your GitHub or Google account
4. Create a new organization (if needed)
5. Create a new project:
   - **Project name**: Enter any name (e.g., "medasis")
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose a region closest to you
   - Click **"Create new project"**

Your project will take about 1-2 minutes to initialize.

## Step 2: Get Your Credentials

Once your project is created:

1. Go to **Settings** (bottom left sidebar)
2. Click **API** in the left menu
3. You'll see:
   - **Project URL**: Copy this (e.g., `https://your-project.supabase.co`)
   - **Project API Keys** section:
     - Copy the **`anon` / `public` key** (not the secret key!)

## Step 3: Configure Environment Variables

1. Create a `.env` file in the project root (if you don't have one)
2. Add these lines with your Supabase credentials:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production

# Supabase Configuration  
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key

# Other configurations
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2-flash
```

Replace:
- `https://your-project.supabase.co` with your actual Project URL
- `your-anon-public-key` with your actual public API key
- `your-secret-key-change-this-in-production` with a random string (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`)

## Step 4: Verify Installation

1. Restart your Flask app:
   ```bash
   # Kill the current app process
   # Then restart it with:
   python app.py
   ```

2. Open your app in browser: `http://localhost:5000`
3. You should see the **Login/Signup page** instead of the main app

## Step 5: Create Your First Account

1. Click **"Sign Up"** on the login page
2. Enter:
   - Full Name: Your name
   - Email: Your email address
   - Password: A password (minimum 6 characters)
3. Click **"Create Account"**
4. You'll be redirected to the main app!

## Features Now Available

✅ **User Authentication**
- Email/password sign up and sign in
- Session management
- Logout functionality

✅ **User Profile Display**
- Shows logged-in user's name and email
- User menu dropdown

✅ **Protected Routes**
- All app features require login
- Automatic redirect to login if session expires

## Troubleshooting

### "Authentication service not configured"
- Check if `SUPABASE_URL` and `SUPABASE_KEY` are set in `.env`
- Restart your Flask app after updating `.env`

### "Invalid login credentials"
- Make sure you're using the correct email and password
- Try signing up with a new account

### Session expires after app restart
- This is normal in development mode
- You'll need to log in again after each app restart
- In production, use persistent session storage

### "Email already registered"
- The email you're trying to use already exists
- Try with a different email address
- Or log in if you already have an account

## API Endpoints

### Public (No Auth Required)
- `POST /api/auth/signin` - Sign in user
- `POST /api/auth/signup` - Create new account

### Protected (Auth Required)
- `GET /api/auth/user` - Get current user info
- `POST /api/auth/logout` - Logout user
- `POST /upload` - Upload medicine image
- `POST /query` - Ask AI questions
- `GET /medicines` - List all medicines
- `DELETE /medicines/<id>` - Delete medicine
- `GET /expiring` - Get expiring medicines

## Next Steps

1. **Customize user profile** - Add more user metadata in Supabase
2. **Add email verification** - Enable email confirmation in Supabase settings
3. **Persistent storage** - Store user-specific medicines with user IDs
4. **Social login** - Add GitHub/Google sign-in via Supabase

For more details, see [Supabase Documentation](https://supabase.com/docs)

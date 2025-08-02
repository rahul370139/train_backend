# 🚀 TrainPI Backend Deployment Guide

## 📋 Prerequisites
- Node.js 18+ installed
- Vercel CLI installed: `npm i -g vercel`
- Git repository set up
- Environment variables ready

## 🔧 Step-by-Step Deployment Process

### Step 1: Environment Setup
```bash
# 1. Set up environment variables
# Create .env file in backend/ directory with:
GROQ_API_KEY=your_groq_api_key_here
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Step 2: Local Testing
```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run tests
python -m pytest tests/ -v

# 4. Run demo to verify functionality
python demo_complete_system.py

# 5. Test FastAPI app loads
python -c "from main import app; print('✅ App loaded successfully!')"
```

### Step 3: Git Preparation
```bash
# 1. Add all files
git add .

# 2. Commit changes
git commit -m "Production ready TrainPI backend"

# 3. Push to repository
git push origin main
```

### Step 4: Vercel Deployment
```bash
# 1. Login to Vercel (if not already logged in)
vercel login

# 2. Deploy to Vercel
vercel --prod

# 3. Follow prompts:
# - Set up and deploy: Yes
# - Which scope: Select your scope
# - Link to existing project: No
# - Project name: trainpi-backend (or your preferred name)
# - Directory: ./backend
# - Override settings: No
```

### Step 5: Environment Variables in Vercel
```bash
# 1. Go to Vercel Dashboard
# 2. Select your project
# 3. Go to Settings > Environment Variables
# 4. Add the following variables:
GROQ_API_KEY=your_groq_api_key_here
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Step 6: Verify Deployment
```bash
# 1. Get your deployment URL from Vercel dashboard
# 2. Test the deployment
python test_deployment.py https://your-app.vercel.app

# 3. Check all endpoints are working
curl https://your-app.vercel.app/api/frameworks
```

## 🔍 Troubleshooting

### Common Issues:
1. **Module not found errors**: Ensure all dependencies are in requirements.txt
2. **Environment variables not found**: Check Vercel environment variables
3. **CORS issues**: Frontend needs to use correct backend URL
4. **API key errors**: Verify GROQ_API_KEY is set correctly

### Debug Commands:
```bash
# Check if app loads locally
python -c "from main import app; print('OK')"

# Test specific endpoint
curl -X POST http://localhost:8000/api/frameworks

# Check Vercel logs
vercel logs
```

## 📊 Post-Deployment Checklist
- [ ] All tests passing locally
- [ ] Demo runs successfully
- [ ] Environment variables set in Vercel
- [ ] Deployment URL accessible
- [ ] All endpoints responding correctly
- [ ] Frontend can connect to backend
- [ ] Documentation updated with new URLs

## 🎯 Production URLs
After deployment, your endpoints will be available at:
- Base URL: `https://your-app.vercel.app`
- API Base: `https://your-app.vercel.app/api`
- Health Check: `https://your-app.vercel.app/api/frameworks`

## 📝 Notes
- The backend uses Vercel serverless functions
- Each API call is stateless
- Database connections are handled per request
- LLM calls use Groq API for fast responses
- All data is stored in Supabase 
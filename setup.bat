@echo off
echo 🚀 Setting up Aionix Agent...
echo.

echo 📦 Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install backend dependencies
    pause
    exit /b 1
)

echo 🗄️ Setting up database...
python -c "from db.database import init_database; import asyncio; asyncio.run(init_database())"
if %errorlevel% neq 0 (
    echo ❌ Failed to setup database
    pause
    exit /b 1
)

echo 👤 Creating admin user...
python scripts\create_admin_user.py
if %errorlevel% neq 0 (
    echo ❌ Failed to create admin user
    pause
    exit /b 1
)

cd ..
echo.
echo ✅ Backend setup complete!
echo.
echo 🔧 Next steps:
echo 1. Start the backend: python run-backend.py
echo 2. In another terminal, go to frontend and run: npm run dev
echo 3. Open http://localhost:3000 in your browser
echo.
echo 👨‍💼 Admin login:
echo Email: admin@aionix.ai
echo Password: admin123
echo.
pause

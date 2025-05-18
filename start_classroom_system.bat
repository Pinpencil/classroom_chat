@echo off
echo ======================================================
echo             课堂互动系统启动脚本
echo ======================================================
echo.

REM 检查Python是否已安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python安装。
    echo 请先安装Python 3.8或更高版本，然后再运行此脚本。
    echo 您可以从 https://www.python.org/downloads/ 下载Python。
    echo.
    pause
    exit /b 1
)

REM 检查Python版本
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
for /f "tokens=1 delims=." %%a in ("%PYTHON_VERSION%") do set PYTHON_MAJOR=%%a
for /f "tokens=2 delims=." %%a in ("%PYTHON_VERSION%") do set PYTHON_MINOR=%%a

if %PYTHON_MAJOR% lss 3 (
    echo [错误] Python版本过低。需要Python 3.8或更高版本。
    echo 当前版本: %PYTHON_VERSION%
    echo.
    pause
    exit /b 1
)

if %PYTHON_MAJOR% equ 3 (
    if %PYTHON_MINOR% lss 8 (
        echo [错误] Python版本过低。需要Python 3.8或更高版本。
        echo 当前版本: %PYTHON_VERSION%
        echo.
        pause
        exit /b 1
    )
)

echo [信息] 检测到Python %PYTHON_VERSION%

REM 创建必要的目录
if not exist data mkdir data
if not exist logs mkdir logs
if not exist uploads mkdir uploads

REM 检查依赖库是否已安装
echo [信息] 检查依赖库...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装Flask...
    pip install flask
)

python -c "import flask_socketio" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装Flask-SocketIO...
    pip install flask-socketio
)

python -c "import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装pandas...
    pip install pandas
)

REM 配置防火墙
echo [信息] 配置防火墙规则...
netsh advfirewall firewall show rule name="ClassroomChatSystem" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 添加防火墙规则...
    netsh advfirewall firewall add rule name="ClassroomChatSystem" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
    if %errorlevel% neq 0 (
        echo [警告] 无法添加防火墙规则。如果遇到网络访问问题，请以管理员身份运行此脚本。
    ) else (
        echo [信息] 防火墙规则已添加。
    )
) else (
    echo [信息] 防火墙规则已存在。
)

REM 获取本机IP地址
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set IP_ADDRESS=%%a
    goto :found_ip
)
:found_ip
set IP_ADDRESS=%IP_ADDRESS:~1%

echo.
echo ======================================================
echo                 课堂互动系统启动中
echo ======================================================
echo.
echo 本机访问地址: http://localhost:5000
echo 局域网访问地址: http://%IP_ADDRESS%:5000
echo.
echo 其他设备可通过浏览器访问上述局域网地址
echo.
echo 按Ctrl+C可停止服务器
echo ======================================================
echo.

REM 启动Flask应用
cd src
python app.py

pause

import os
import sys
import socket
import subprocess
import webbrowser
import logging
from datetime import datetime

# 设置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'classroom_system_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('classroom_system')

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个临时socket连接来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"获取本机IP失败: {e}")
        return "127.0.0.1"  # 如果获取失败，返回本地回环地址

def configure_firewall():
    """配置Windows防火墙，允许Flask应用通过"""
    if sys.platform != 'win32':
        logger.info("非Windows系统，跳过防火墙配置")
        return
    
    try:
        # 添加防火墙规则允许Flask应用（端口5000）
        rule_name = "ClassroomChatSystem"
        cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol=TCP localport=5000'
        
        # 在Windows上使用管理员权限运行命令
        if sys.platform == 'win32':
            from ctypes import windll
            if windll.shell32.IsUserAnAdmin() == 0:
                logger.warning("需要管理员权限来配置防火墙，请以管理员身份运行")
                print("警告: 需要管理员权限来配置防火墙。如果您看到网络访问问题，请以管理员身份重新运行程序。")
            else:
                subprocess.run(cmd, shell=True, check=True)
                logger.info("防火墙规则已添加")
                print("防火墙规则已成功添加")
    except Exception as e:
        logger.error(f"配置防火墙失败: {e}")
        print(f"配置防火墙时出错: {e}")

def main():
    """主函数，启动Flask应用并显示访问信息"""
    # 配置防火墙
    configure_firewall()
    
    # 获取本机IP
    local_ip = get_local_ip()
    
    # 确保数据目录存在
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)
    
    # 显示访问信息
    print("\n" + "="*50)
    print("课堂互动系统启动中...")
    print("="*50)
    print(f"本机访问地址: http://localhost:5000")
    print(f"局域网访问地址: http://{local_ip}:5000")
    print("其他设备可通过浏览器访问上述局域网地址")
    print("="*50 + "\n")
    
    # 记录启动信息
    logger.info(f"系统启动 - 本地地址: http://localhost:5000, 局域网地址: http://{local_ip}:5000")
    
    # 自动打开浏览器
    webbrowser.open(f"http://localhost:5000")
    
    # 启动Flask应用
    try:
        # 导入app模块
        from app import app
        # 启动Flask应用
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"启动Flask应用失败: {e}")
        print(f"错误: 启动应用失败 - {e}")
        input("按Enter键退出...")

if __name__ == "__main__":
    main()

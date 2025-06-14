# 课堂互动系统 - 快速部署指南

## 系统简介

课堂互动系统是一个基于局域网的教学辅助工具，支持教师创建聊天室、导入学生名单，学生可以进行签到、留言、答题等活动。系统完全在局域网内运行，不需要连接互联网。

## 部署步骤

### 1. 系统要求

- Windows 10/11 操作系统
- Python 3.8 或更高版本（如未安装，启动脚本会提示您安装）
- 局域网环境

### 2. 快速启动

1. 解压下载的ZIP文件到任意位置
2. 双击 `start_classroom_system.bat` 文件
3. 脚本会自动：
   - 检查Python安装
   - 安装必要的依赖库
   - 配置防火墙规则
   - 显示访问地址
   - 启动系统

### 3. 访问系统

- 在服务器电脑上：通过浏览器访问 `http://localhost:5000`
- 在局域网内其他设备上：通过浏览器访问 `http://[服务器IP]:5000`
  （启动脚本会显示具体的IP地址）

## 文件夹结构说明

- `src/` - 系统源代码
- `data/` - 数据存储目录
- `logs/` - 日志文件目录
- `uploads/` - 上传文件存储目录
- `icons/` - 系统图标

## 常见问题解决

### 无法启动系统

- 确保已安装Python 3.8或更高版本
- 尝试以管理员身份运行启动脚本

### 其他设备无法访问

- 确认防火墙设置（可能需要以管理员身份运行启动脚本）
- 确保所有设备在同一局域网内
- 检查IP地址是否正确

### 更多帮助

详细的系统使用说明请参考 `user_manual.md` 文件。

## 注意事项

- 系统数据存储在 `data` 目录中，请定期备份
- 如需重置系统，可删除 `data` 目录中的数据库文件
- 启动脚本会自动安装所需的Python库，首次运行可能需要一些时间

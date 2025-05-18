from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
import json
import pandas as pd
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# 确保数据库目录存在
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DB_PATH, exist_ok=True)
DB_FILE = os.path.join(DB_PATH, 'classroom.db')

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建聊天室表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chatrooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        active BOOLEAN DEFAULT 1,
        FOREIGN KEY (creator_id) REFERENCES users (id)
    )
    ''')
    
    # 创建聊天室成员表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chatroom_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatroom_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatroom_id) REFERENCES chatrooms (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 创建消息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER,
        chatroom_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        FOREIGN KEY (chatroom_id) REFERENCES chatrooms (id)
    )
    ''')
    
    # 创建题目表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatroom_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        options TEXT,
        answer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatroom_id) REFERENCES chatrooms (id),
        FOREIGN KEY (creator_id) REFERENCES users (id)
    )
    ''')
    
    # 创建答题记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        score REAL,
        FOREIGN KEY (question_id) REFERENCES questions (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 创建签到表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatroom_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expire_at TIMESTAMP,
        FOREIGN KEY (chatroom_id) REFERENCES chatrooms (id)
    )
    ''')
    
    # 创建签到记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (attendance_id) REFERENCES attendance (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

# 辅助函数：获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# 路由：首页
@app.route('/')
def index():
    return render_template('index.html')

# 路由：教师登录页面
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        teacher = conn.execute('SELECT * FROM users WHERE name = ? AND role = ?', 
                              (username, 'teacher')).fetchone()
        conn.close()
        
        if teacher and check_password_hash(teacher['password'], password):
            session['user_id'] = teacher['id']
            session['user_name'] = teacher['name']
            session['user_role'] = 'teacher'
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('teacher_login.html', error='用户名或密码错误')
    
    return render_template('teacher_login.html')

# 路由：教师注册页面（首次使用时）
@app.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        existing_teacher = conn.execute('SELECT * FROM users WHERE name = ? AND role = ?', 
                                      (username, 'teacher')).fetchone()
        
        if existing_teacher:
            conn.close()
            return render_template('teacher_register.html', error='该用户名已存在')
        
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (name, role, password) VALUES (?, ?, ?)', 
                    (username, 'teacher', hashed_password))
        conn.commit()
        
        teacher = conn.execute('SELECT * FROM users WHERE name = ? AND role = ?', 
                              (username, 'teacher')).fetchone()
        conn.close()
        
        session['user_id'] = teacher['id']
        session['user_name'] = teacher['name']
        session['user_role'] = 'teacher'
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('teacher_register.html')

# 路由：教师仪表板
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if not session.get('user_id') or session.get('user_role') != 'teacher':
        return redirect(url_for('teacher_login'))
    
    conn = get_db_connection()
    chatrooms = conn.execute('SELECT * FROM chatrooms WHERE creator_id = ? ORDER BY created_at DESC', 
                           (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('teacher_dashboard.html', chatrooms=chatrooms)

# 路由：导入学生名单
@app.route('/teacher/import_students', methods=['GET', 'POST'])
def import_students():
    if not session.get('user_id') or session.get('user_role') != 'teacher':
        return redirect(url_for('teacher_login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('import_students.html', error='没有选择文件')
        
        file = request.files['file']
        if file.filename == '':
            return render_template('import_students.html', error='没有选择文件')
        
        if file and file.filename.endswith(('.xls', '.xlsx')):
            try:
                # 保存上传的文件
                file_path = os.path.join(os.path.dirname(__file__), '..', 'uploads', file.filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                # 读取Excel文件
                df = pd.read_excel(file_path)
                
                # 检查是否有"姓名"列
                if '姓名' not in df.columns:
                    return render_template('import_students.html', error='Excel文件必须包含"姓名"列')
                
                # 导入学生名单
                conn = get_db_connection()
                for _, row in df.iterrows():
                    name = row['姓名']
                    conn.execute('INSERT INTO users (name, role) VALUES (?, ?)', 
                                (name, 'student'))
                
                conn.commit()
                conn.close()
                
                return redirect(url_for('teacher_dashboard'))
            except Exception as e:
                return render_template('import_students.html', error=f'导入失败：{str(e)}')
        
        return render_template('import_students.html', error='不支持的文件格式')
    
    return render_template('import_students.html')

# 路由：创建聊天室
@app.route('/teacher/create_chatroom', methods=['GET', 'POST'])
def create_chatroom():
    if not session.get('user_id') or session.get('user_role') != 'teacher':
        return redirect(url_for('teacher_login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        
        conn = get_db_connection()
        cursor = conn.execute('INSERT INTO chatrooms (name, creator_id) VALUES (?, ?)', 
                            (name, session['user_id']))
        chatroom_id = cursor.lastrowid
        
        # 获取所有学生
        students = conn.execute('SELECT * FROM users WHERE role = ?', ('student',)).fetchall()
        
        # 将学生添加到聊天室
        for student in students:
            conn.execute('INSERT INTO chatroom_members (chatroom_id, user_id) VALUES (?, ?)', 
                        (chatroom_id, student['id']))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_chatroom.html')

# 路由：学生选择页面
@app.route('/student')
def student_select():
    conn = get_db_connection()
    chatrooms = conn.execute('SELECT * FROM chatrooms WHERE active = 1 ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('student_select.html', chatrooms=chatrooms)

# 路由：学生选择聊天室
@app.route('/student/chatroom/<int:chatroom_id>')
def student_chatroom_select(chatroom_id):
    conn = get_db_connection()
    chatroom = conn.execute('SELECT * FROM chatrooms WHERE id = ?', (chatroom_id,)).fetchone()
    
    if not chatroom:
        conn.close()
        return redirect(url_for('student_select'))
    
    students = conn.execute('''
        SELECT u.* FROM users u
        JOIN chatroom_members cm ON u.id = cm.user_id
        WHERE cm.chatroom_id = ? AND u.role = ?
    ''', (chatroom_id, 'student')).fetchall()
    
    conn.close()
    
    return render_template('student_name_select.html', chatroom=chatroom, students=students)

# 路由：学生选择姓名
@app.route('/student/select_name', methods=['POST'])
def student_select_name():
    user_id = request.form.get('user_id')
    chatroom_id = request.form.get('chatroom_id')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if not user:
        return redirect(url_for('student_select'))
    
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_role'] = 'student'
    session['chatroom_id'] = chatroom_id
    
    return redirect(url_for('chatroom', chatroom_id=chatroom_id))

# 路由：聊天室页面
@app.route('/chatroom/<int:chatroom_id>')
def chatroom(chatroom_id):
    if not session.get('user_id'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    chatroom = conn.execute('SELECT * FROM chatrooms WHERE id = ?', (chatroom_id,)).fetchone()
    
    if not chatroom:
        conn.close()
        return redirect(url_for('index'))
    
    # 获取聊天室成员
    members = conn.execute('''
        SELECT u.* FROM users u
        JOIN chatroom_members cm ON u.id = cm.user_id
        WHERE cm.chatroom_id = ?
    ''', (chatroom_id,)).fetchall()
    
    # 获取公共消息
    public_messages = conn.execute('''
        SELECT m.*, u.name as sender_name FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.chatroom_id = ? AND m.type = 'public'
        ORDER BY m.sent_at ASC
    ''', (chatroom_id,)).fetchall()
    
    # 获取私人消息
    private_messages = conn.execute('''
        SELECT m.*, u.name as sender_name, ur.name as receiver_name FROM messages m
        JOIN users u ON m.sender_id = u.id
        JOIN users ur ON m.receiver_id = ur.id
        WHERE m.chatroom_id = ? AND m.type = 'private'
        AND (m.sender_id = ? OR m.receiver_id = ?)
        ORDER BY m.sent_at ASC
    ''', (chatroom_id, session['user_id'], session['user_id'])).fetchall()
    
    # 获取题目
    questions = conn.execute('''
        SELECT q.*, u.name as creator_name FROM questions q
        JOIN users u ON q.creator_id = u.id
        WHERE q.chatroom_id = ?
        ORDER BY q.created_at DESC
    ''', (chatroom_id,)).fetchall()
    
    # 获取签到
    attendances = conn.execute('''
        SELECT a.* FROM attendance a
        WHERE a.chatroom_id = ? AND (a.expire_at IS NULL OR a.expire_at > datetime('now'))
        ORDER BY a.created_at DESC
    ''', (chatroom_id,)).fetchall()
    
    # 获取已签到记录
    attendance_records = conn.execute('''
        SELECT ar.* FROM attendance_records ar
        JOIN attendance a ON ar.attendance_id = a.id
        WHERE a.chatroom_id = ? AND ar.user_id = ?
    ''', (chatroom_id, session['user_id'])).fetchall()
    
    conn.close()
    
    return render_template('chatroom.html', 
                          chatroom=chatroom, 
                          members=members, 
                          public_messages=public_messages, 
                          private_messages=private_messages,
                          questions=questions,
                          attendances=attendances,
                          attendance_records=attendance_records)

# API：发送公共消息
@app.route('/api/message/public', methods=['POST'])
def send_public_message():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    content = data.get('content')
    chatroom_id = data.get('chatroom_id')
    
    if not content or not chatroom_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO messages (sender_id, chatroom_id, content, type)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], chatroom_id, content, 'public'))
    
    message_id = cursor.lastrowid
    
    # 获取发送者信息
    sender = conn.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    conn.commit()
    conn.close()
    
    # 通过WebSocket广播消息
    socketio.emit('new_message', {
        'id': message_id,
        'sender_id': session['user_id'],
        'sender_name': sender['name'],
        'content': content,
        'type': 'public',
        'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'chatroom_{chatroom_id}')
    
    return jsonify({'success': True})

# API：发送私人消息
@app.route('/api/message/private', methods=['POST'])
def send_private_message():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    content = data.get('content')
    chatroom_id = data.get('chatroom_id')
    receiver_id = data.get('receiver_id')
    
    if not content or not chatroom_id or not receiver_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, chatroom_id, content, type)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], receiver_id, chatroom_id, content, 'private'))
    
    message_id = cursor.lastrowid
    
    # 获取发送者和接收者信息
    sender = conn.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    receiver = conn.execute('SELECT name FROM users WHERE id = ?', (receiver_id,)).fetchone()
    
    conn.commit()
    conn.close()
    
    # 通过WebSocket发送给接收者
    socketio.emit('new_private_message', {
        'id': message_id,
        'sender_id': session['user_id'],
        'sender_name': sender['name'],
        'receiver_id': receiver_id,
        'receiver_name': receiver['name'],
        'content': content,
        'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'user_{receiver_id}')
    
    # 同时发送给发送者
    socketio.emit('new_private_message', {
        'id': message_id,
        'sender_id': session['user_id'],
        'sender_name': sender['name'],
        'receiver_id': receiver_id,
        'receiver_name': receiver['name'],
        'content': content,
        'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'user_{session["user_id"]}')
    
    return jsonify({'success': True})

# API：创建题目
@app.route('/api/question/create', methods=['POST'])
def create_question():
    if not session.get('user_id') or session.get('user_role') != 'teacher':
        return jsonify({'success': False, 'error': '未授权'}), 403
    
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    question_type = data.get('type')
    options = data.get('options')
    answer = data.get('answer')
    chatroom_id = data.get('chatroom_id')
    
    if not title or not content or not question_type or not chatroom_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    # 选择题必须有选项
    if question_type == 'choice' and (not options or not answer):
        return jsonify({'success': False, 'error': '选择题必须有选项和答案'}), 400
    
    conn = get_db_connection()
    
    # 将选项转换为JSON字符串
    options_json = json.dumps(options) if options else None
    
    cursor = conn.execute('''
        INSERT INTO questions (chatroom_id, creator_id, title, content, type, options, answer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chatroom_id, session['user_id'], title, content, question_type, options_json, answer))
    
    question_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # 通过WebSocket广播新题目
    socketio.emit('new_question', {
        'id': question_id,
        'title': title,
        'content': content,
        'type': question_type,
        'options': options,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'chatroom_{chatroom_id}')
    
    return jsonify({'success': True, 'question_id': question_id})

# API：提交答案
@app.route('/api/question/answer', methods=['POST'])
def submit_answer():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    question_id = data.get('question_id')
    content = data.get('content')
    
    if not question_id or not content:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db_connection()
    
    # 检查是否已经回答过
    existing_answer = conn.execute('''
        SELECT * FROM answers WHERE question_id = ? AND user_id = ?
    ''', (question_id, session['user_id'])).fetchone()
    
    if existing_answer:
        conn.close()
        return jsonify({'success': False, 'error': '已经回答过该题目'}), 400
    
    # 获取题目信息
    question = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    
    if not question:
        conn.close()
        return jsonify({'success': False, 'error': '题目不存在'}), 404
    
    # 自动评分（仅选择题）
    score = None
    if question['type'] == 'choice' and question['answer']:
        if content == question['answer']:
            score = 100.0
        else:
            score = 0.0
    
    cursor = conn.execute('''
        INSERT INTO answers (question_id, user_id, content, score)
        VALUES (?, ?, ?, ?)
    ''', (question_id, session['user_id'], content, score))
    
    answer_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # 通知教师有新答案（如果是教师创建的题目）
    if question['creator_id']:
        socketio.emit('new_answer', {
            'answer_id': answer_id,
            'question_id': question_id,
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'content': content,
            'score': score,
            'submitted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, room=f'user_{question["creator_id"]}')
    
    return jsonify({'success': True, 'answer_id': answer_id, 'score': score})

# API：创建签到
@app.route('/api/attendance/create', methods=['POST'])
def create_attendance():
    if not session.get('user_id') or session.get('user_role') != 'teacher':
        return jsonify({'success': False, 'error': '未授权'}), 403
    
    data = request.get_json()
    title = data.get('title')
    attendance_type = data.get('type')
    password = data.get('password')
    chatroom_id = data.get('chatroom_id')
    expire_minutes = data.get('expire_minutes')
    
    if not title or not attendance_type or not chatroom_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    # 密码签到必须有密码
    if attendance_type == 'password' and not password:
        return jsonify({'success': False, 'error': '密码签到必须设置密码'}), 400
    
    conn = get_db_connection()
    
    # 计算过期时间
    expire_at = None
    if expire_minutes:
        expire_at = datetime.now().replace(microsecond=0) + pd.Timedelta(minutes=int(expire_minutes))
    
    cursor = conn.execute('''
        INSERT INTO attendance (chatroom_id, title, type, password, expire_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (chatroom_id, title, attendance_type, password, expire_at))
    
    attendance_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # 通过WebSocket广播新签到
    socketio.emit('new_attendance', {
        'id': attendance_id,
        'title': title,
        'type': attendance_type,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expire_at': expire_at.strftime('%Y-%m-%d %H:%M:%S') if expire_at else None
    }, room=f'chatroom_{chatroom_id}')
    
    return jsonify({'success': True, 'attendance_id': attendance_id})

# API：学生签到
@app.route('/api/attendance/sign', methods=['POST'])
def student_sign():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    attendance_id = data.get('attendance_id')
    password = data.get('password')
    
    if not attendance_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    conn = get_db_connection()
    
    # 检查签到是否存在且未过期
    attendance = conn.execute('''
        SELECT * FROM attendance 
        WHERE id = ? AND (expire_at IS NULL OR expire_at > datetime('now'))
    ''', (attendance_id,)).fetchone()
    
    if not attendance:
        conn.close()
        return jsonify({'success': False, 'error': '签到不存在或已过期'}), 404
    
    # 检查是否已经签到
    existing_record = conn.execute('''
        SELECT * FROM attendance_records WHERE attendance_id = ? AND user_id = ?
    ''', (attendance_id, session['user_id'])).fetchone()
    
    if existing_record:
        conn.close()
        return jsonify({'success': False, 'error': '已经签到过'}), 400
    
    # 检查密码（如果是密码签到）
    if attendance['type'] == 'password' and password != attendance['password']:
        conn.close()
        return jsonify({'success': False, 'error': '签到密码错误'}), 400
    
    cursor = conn.execute('''
        INSERT INTO attendance_records (attendance_id, user_id)
        VALUES (?, ?)
    ''', (attendance_id, session['user_id']))
    
    record_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # 通知教师有新签到
    socketio.emit('new_attendance_record', {
        'record_id': record_id,
        'attendance_id': attendance_id,
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'signed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'chatroom_{attendance["chatroom_id"]}')
    
    return jsonify({'success': True, 'record_id': record_id})

# WebSocket：加入聊天室
@socketio.on('join')
def on_join(data):
    chatroom_id = data.get('chatroom_id')
    
    if not chatroom_id or not session.get('user_id'):
        return
    
    # 加入聊天室房间
    join_room(f'chatroom_{chatroom_id}')
    
    # 加入用户私人房间
    join_room(f'user_{session["user_id"]}')
    
    # 通知其他人
    emit('user_joined', {
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'joined_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'chatroom_{chatroom_id}', include_self=False)

# WebSocket：离开聊天室
@socketio.on('leave')
def on_leave(data):
    chatroom_id = data.get('chatroom_id')
    
    if not chatroom_id or not session.get('user_id'):
        return
    
    # 离开聊天室房间
    leave_room(f'chatroom_{chatroom_id}')
    
    # 通知其他人
    emit('user_left', {
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'left_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'chatroom_{chatroom_id}')

# 路由：退出登录
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 启动应用
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

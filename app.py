from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import pytz
from user_manager import UserManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# กำหนดค่าสำหรับการอัปโหลดไฟล์
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}

# สร้างโฟลเดอร์ถ้ายังไม่มี
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัดขนาดไฟล์ที่ 16MB

# สร้าง instance ของ UserManager
user_manager = UserManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(filepath):
    return os.path.getsize(filepath)

def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def get_thai_datetime(dt):
    thai_tz = pytz.timezone('Asia/Bangkok')
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    thai_dt = dt.astimezone(thai_tz)
    
    # แปลงปีเป็นปี พ.ศ.
    thai_year = thai_dt.year + 543
    
    # จัดรูปแบบวันที่เป็น dd/mm/yyyy
    return f"{thai_dt.day:02d}/{thai_dt.month:02d}/{thai_year}"

@app.template_filter('datetimeformat_th')
def datetimeformat_th(value):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return get_thai_datetime(value)

@app.template_filter('filesize')
def filesize_filter(size):
    return format_file_size(size)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    per_page = 10
    files = []
    
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):  # ตรวจสอบว่าเป็นไฟล์
                file_stat = os.stat(filepath)
                file_data = {
                    'name': filename,
                    'size': get_file_size(filepath),
                    'date': datetime.fromtimestamp(file_stat.st_mtime, pytz.UTC)
                }
                
                # กรองตามการค้นหา
                if search_query and search_query.lower() not in filename.lower():
                    continue
                    
                # กรองตามวันที่
                if start_date and end_date:
                    file_date = file_data['date'].date()
                    start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end = datetime.strptime(end_date, '%Y-%m-%d').date()
                    if not (start <= file_date <= end):
                        continue
                        
                files.append(file_data)
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}')
        files = []
    
    # เรียงตามวันที่ล่าสุด
    files.sort(key=lambda x: x['date'], reverse=True)
    
    # การแบ่งหน้า
    total_files = len(files)
    total_pages = (total_files + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    files = files[start:end]
    
    return render_template('index.html', 
                         files=files,
                         total_files=total_files,
                         page=page,
                         total_pages=total_pages,
                         search_query=search_query,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if not user_manager.is_admin(session['username']):
        flash('คุณไม่มีสิทธิ์อัปโหลดไฟล์')
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('ไม่พบไฟล์ที่ต้องการอัปโหลด')
        return redirect(url_for('index'))
        
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        flash('กรุณาเลือกไฟล์ที่ต้องการอัปโหลด')
        return redirect(url_for('index'))

    upload_success = False
    
    for file in files:
        if file and file.filename:
            try:
                filename = secure_filename(file.filename)
                
                # เช็คนามสกุลไฟล์
                if not allowed_file(filename):
                    flash(f'ไม่อนุญาตให้อัปโหลดไฟล์ {filename} (รองรับเฉพาะไฟล์ {", ".join(ALLOWED_EXTENSIONS)})')
                    continue

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # เช็คไฟล์ซ้ำ
                if os.path.exists(file_path):
                    # สร้างชื่อไฟล์ใหม่โดยเพิ่มตัวเลขต่อท้าย
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(file_path):
                        new_filename = f"{name}_{counter}{ext}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                        counter += 1
                    filename = os.path.basename(file_path)
                    flash(f'มีไฟล์ {file.filename} อยู่แล้ว บันทึกเป็น {filename}')

                # บันทึกไฟล์
                file.save(file_path)
                
                # ตรวจสอบว่าไฟล์ถูกบันทึกจริง
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    upload_success = True
                    flash(f'อัปโหลดไฟล์ {filename} สำเร็จ')
                else:
                    flash(f'เกิดข้อผิดพลาดในการบันทึกไฟล์ {filename}')
                    
            except Exception as e:
                flash(f'เกิดข้อผิดพลาดในการอัปโหลดไฟล์ {file.filename}: {str(e)}')
                continue
    
    if not upload_success:
        flash('ไม่สามารถอัปโหลดไฟล์ได้')
            
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการดาวน์โหลดไฟล์: {str(e)}')
        return redirect(url_for('index'))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if not user_manager.is_admin(session['username']):
        flash('คุณไม่มีสิทธิ์ลบไฟล์')
        return redirect(url_for('index'))
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f'ลบไฟล์ {filename} สำเร็จ')
        else:
            flash(f'ไม่พบไฟล์ {filename}')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการลบไฟล์: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if user_manager.verify_user(username, password):
            session['username'] = username
            flash('เข้าสู่ระบบสำเร็จ')
            return redirect(url_for('index'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('ออกจากระบบสำเร็จ')
    return redirect(url_for('login'))

@app.route('/users')
def manage_users():
    if not user_manager.is_admin(session.get('username')):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect(url_for('index'))
    
    return render_template('users.html', 
                         users=user_manager.get_users())

@app.route('/add_user', methods=['POST'])
def add_user():
    if not user_manager.is_admin(session.get('username')):
        flash('คุณไม่มีสิทธิ์ดำเนินการนี้')
        return redirect(url_for('index'))
    
    username = request.form['username']
    password = request.form['password']
    
    if user_manager.add_user(username, password):
        flash(f'เพิ่มผู้ใช้ {username} สำเร็จ')
    else:
        flash('ชื่อผู้ใช้นี้มีอยู่แล้ว')
    
    return redirect(url_for('manage_users'))

@app.route('/edit_user', methods=['POST'])
def edit_user():
    if not user_manager.is_admin(session.get('username')):
        flash('คุณไม่มีสิทธิ์ดำเนินการนี้')
        return redirect(url_for('index'))
    
    username_old = request.form['username_old']
    username_new = request.form['username_new']
    password = request.form['password'] or None
    
    if user_manager.update_user(username_old, username_new, password):
        flash(f'แก้ไขข้อมูลผู้ใช้สำเร็จ')
    else:
        flash('ไม่สามารถแก้ไขข้อมูลผู้ใช้ได้')
    
    return redirect(url_for('manage_users'))

@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if not user_manager.is_admin(session.get('username')):
        flash('คุณไม่มีสิทธิ์ดำเนินการนี้')
        return redirect(url_for('index'))
    
    if user_manager.delete_user(username):
        flash(f'ลบผู้ใช้ {username} สำเร็จ')
    else:
        flash('ไม่สามารถลบผู้ใช้นี้ได้')
    
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
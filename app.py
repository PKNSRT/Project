from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretkey'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(directory, filename):
    """
    If a file name already exists, add a number 1, 2, 3... after the filename before the extension
    """
    basename, ext = os.path.splitext(filename)
    counter = 1
    unique_name = filename
    while os.path.exists(os.path.join(directory, unique_name)):
        unique_name = f"{basename} ({counter}){ext}"
        counter += 1
    return unique_name

@app.template_filter('datetimeformat_th')
def datetimeformat_th(value):
    dt = datetime.strptime(value, "%Y-%m-%d")
    return dt.strftime("%d/%m/%Y")  # Day/Month/Year

@app.route('/')
def index():
    page = int(request.args.get('page', 1))
    per_page = 10
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    files = []
    for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER']), reverse=True):
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(path):
            upload_time = datetime.fromtimestamp(os.path.getctime(path))
            files.append({
                'name': filename,
                'date': upload_time.strftime('%Y-%m-%d'),
                'datetime': upload_time
            })

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            files = [f for f in files if start <= f['datetime'] <= end]
        except ValueError:
            flash('Invalid date format')

    total_files = len(files)
    total_pages = (total_files + per_page - 1) // per_page
    files = files[(page - 1) * per_page : page * per_page]

    return render_template(
        'index.html',
        files=files,
        page=page,
        total_pages=total_pages,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part found')
        return redirect(url_for('index'))

    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('Please select at least one file')
        return redirect(url_for('index'))

    success_count = 0
    error_files = []

    for file in files:
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            error_files.append(filename)
            continue
        filename = get_unique_filename(app.config['UPLOAD_FOLDER'], filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        success_count += 1

    if success_count > 0:
        flash(f'Successfully uploaded {success_count} file(s)')
    if error_files:
        flash(f'Some files were not allowed: {", ".join(error_files)}')

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash('File deleted successfully')
        except Exception as e:
            flash(f'Error occurred while deleting file: {e}')
    else:
        flash('File to delete not found')
    return redirect(url_for('index'))


# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

from flask import Flask, request, render_template, redirect, url_for, flash
from flask_paginate import Pagination, get_page_args
import sqlite3
from datetime import datetime
import time
from PIL import Image
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # مطلوب لعرض الإشعارات باستخدام flash

# إعداد قاعدة البيانات
def init_db():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS Archive_OM (
                     ID INTEGER PRIMARY KEY AUTOINCREMENT,
                     type TEXT,
                     amount TEXT,
                     Type_amount TEXT,
                     R_Name TEXT,
                     S_Name TEXT,
                     Bond_N TEXT UNIQUE,
                     image TEXT UNIQUE,
                     note TEXT,
                     pass TEXT,
                     type_path TEXT,
                     favorite TEXT,
                     status TEXT,
                     n_phone TEXT,
                     year TEXT,
                     manth TEXT,
                     day TEXT,
                     taim TEXT,
                     enterer TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS T_images (
                     ID INTEGER PRIMARY KEY AUTOINCREMENT,
                     image_path TEXT,
                     namber TEXT,
                     type TEXT,
                     type_path TEXT,
                     favorite TEXT,
                     year TEXT,
                     manth TEXT,
                     day TEXT,
                     taim TEXT,
                     enterer TEXT)''')
        conn.commit()

# تشغيل قاعدة البيانات
init_db()

# دالة لضغط الصورة وتحويلها إلى Base64
def compress_image(file, max_size=(800, 800), quality=85):
    img = Image.open(file)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# الصفحة الرئيسية مع ترقيم الصفحات
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    search_column = request.args.get('search_column', 'all')
    sort_by = request.args.get('sort_by', 'ID')
    sort_order = request.args.get('sort_order', 'desc')

    valid_columns = ['ID', 'type', 'R_Name', 'Bond_N', 'note', 'year', 'manth', 'day']
    if sort_by not in valid_columns:
        sort_by = 'ID'

    sort_order = 'ASC' if sort_order == 'asc' else 'DESC'

    # ترقيم الصفحات
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = 10  # عدد السجلات لكل صفحة
    offset = (page - 1) * per_page

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if search_query:
        if search_column in valid_columns:
            c.execute(f"SELECT COUNT(*) FROM Archive_OM WHERE {search_column} LIKE ?", ('%' + search_query + '%',))
            total = c.fetchone()[0]
            c.execute(f"SELECT ID, type, R_Name, Bond_N, note, year, manth, day FROM Archive_OM WHERE {search_column} LIKE ? ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?",
                      ('%' + search_query + '%', per_page, offset))
        else:
            c.execute(f"""SELECT COUNT(*) FROM Archive_OM
                          WHERE type LIKE ? OR R_Name LIKE ? OR Bond_N LIKE ? OR note LIKE ? OR year LIKE ? OR manth LIKE ? OR day LIKE ?""",
                      ('%' + search_query + '%',) * 7)
            total = c.fetchone()[0]
            c.execute(f"""SELECT ID, type, R_Name, Bond_N, note, year, manth, day
                          FROM Archive_OM
                          WHERE type LIKE ? OR R_Name LIKE ? OR Bond_N LIKE ? OR note LIKE ? OR year LIKE ? OR manth LIKE ? OR day LIKE ?
                          ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?""",
                      ('%' + search_query + '%',) * 7 + (per_page, offset))
    else:
        c.execute("SELECT COUNT(*) FROM Archive_OM")
        total = c.fetchone()[0]
        c.execute(f"SELECT ID, type, R_Name, Bond_N, note, year, manth, day FROM Archive_OM ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?",
                  (per_page, offset))

    records = c.fetchall()
    conn.close()

    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap5')

    next_sort_order = 'asc' if sort_order == 'DESC' else 'desc'

    return render_template('index.html', records=records, search_query=search_query,
                           search_column=search_column, sort_by=sort_by, sort_order=sort_order,
                           next_sort_order=next_sort_order, pagination=pagination)

# عرض تفاصيل السجل والصور
@app.route('/view/<int:id>')
def view_record(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT ID, type, R_Name, Bond_N, note, year, manth, day, image, type_path, favorite, status, n_phone, taim, enterer FROM Archive_OM WHERE ID = ?", (id,))
    record = c.fetchone()
    if record:
        image_value = record[8]  # قيمة image من Archive_OM
        c.execute("SELECT image_path FROM T_images WHERE namber = ?", (image_value,))
        images = c.fetchall()
    else:
        images = []
    conn.close()
    return render_template('view.html', record=record, images=images)

# إضافة سجل جديد
@app.route('/add', methods=['POST'])
def add_record():
    type_ = request.form['type']
    R_Name = request.form['R_Name']
    Bond_N = request.form['Bond_N']
    note = request.form['note']
    date = request.form['date']  # سيتم تقسيمه في JavaScript

    # القيم الافتراضية
    taim = str(int(time.time() * 1000))
    n_phone = str(request.user_agent)
    image = f"{Bond_N}_{taim}"
    type_path = ''
    favorite = ''
    status = ''
    enterer = ''
    amount = ''
    Type_amount = ''
    S_Name = ''
    pass_ = ''

    # تقسيم التاريخ إلى year, manth, day
    year, manth, day = date.split('-') if date else ('', '', '')

    # التحقق من تكرار Bond_N
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT ID FROM Archive_OM WHERE Bond_N = ?", (Bond_N,))
    if c.fetchone():
        conn.close()
        flash('رقم السند موجود بالفعل! الرجاء اختيار رقم آخر.', 'danger')
        return redirect(url_for('index'))

    c.execute("""INSERT INTO Archive_OM (type, amount, Type_amount, R_Name, S_Name, Bond_N, image, note, pass, type_path, favorite, status, n_phone, year, manth, day, taim, enterer)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (type_, amount, Type_amount, R_Name, S_Name, Bond_N, image, note, pass_, type_path, favorite, status, n_phone, year, manth, day, taim, enterer))
    
    # معالجة الصور المرفوعة
    images = request.files.getlist('images')
    for img_file in images:
        if img_file and img_file.filename:
            image_base64 = compress_image(img_file)
            c.execute("""INSERT INTO T_images (image_path, namber, type, type_path, favorite, year, manth, day, taim, enterer)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (image_base64, image, type_, type_path, favorite, year, manth, day, taim, enterer))
    
    conn.commit()
    conn.close()
    flash('تم إضافة السجل بنجاح!', 'success')
    return redirect(url_for('index'))

# تعديل سجل
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        type_ = request.form['type']
        R_Name = request.form['R_Name']
        Bond_N = request.form['Bond_N']
        note = request.form['note']
        date = request.form['date']
        
        # تقسيم التاريخ
        year, manth, day = date.split('-') if date else ('', '', '')
        
        taim = str(int(time.time() * 1000))
        
        # جلب قيمة image الحالية
        c.execute("SELECT image FROM Archive_OM WHERE ID = ?", (id,))
        image = c.fetchone()[0]
        
        # التحقق من تكرار Bond_N
        c.execute("SELECT ID FROM Archive_OM WHERE Bond_N = ? AND ID != ?", (Bond_N, id))
        if c.fetchone():
            conn.close()
            flash('رقم السند موجود بالفعل! الرجاء اختيار رقم آخر.', 'danger')
            return redirect(url_for('edit_record', id=id))

        c.execute("""UPDATE Archive_OM SET type = ?, R_Name = ?, Bond_N = ?, note = ?, year = ?, manth = ?, day = ?, taim = ?
                     WHERE ID = ?""",
                  (type_, R_Name, Bond_N, note, year, manth, day, taim, id))
        
        # إضافة الصور الجديدة باستخدام قيمة image الحالية كـ namber
        images = request.files.getlist('images')
        for img_file in images:
            if img_file and img_file.filename:
                image_base64 = compress_image(img_file)
                c.execute("""INSERT INTO T_images (image_path, namber, type, type_path, favorite, year, manth, day, taim, enterer)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (image_base64, image, type_, '', '', year, manth, day, taim, ''))
        
        conn.commit()
        conn.close()
        flash('تم تعديل السجل بنجاح!', 'success')
        return redirect(url_for('index'))
    
    c.execute("SELECT ID, type, R_Name, Bond_N, note, year, manth, day FROM Archive_OM WHERE ID = ?", (id,))
    record = c.fetchone()
    conn.close()
    return render_template('edit.html', record=record)

# حذف سجل
@app.route('/delete/<int:id>')
def delete_record(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM T_images WHERE namber = (SELECT image FROM Archive_OM WHERE ID = ?)", (id,))
    c.execute("DELETE FROM Archive_OM WHERE ID = ?", (id,))
    conn.commit()
    conn.close()
    flash('تم حذف السجل بنجاح!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
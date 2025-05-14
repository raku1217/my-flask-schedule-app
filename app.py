from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite を使用
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# データベースとテーブルを作成する
with app.app_context():
    db.create_all()

def build_counts(day, period):
    counts = {}
    for subj, slots in schedule_counts[day][period].items():
        for s, c in slots.items():
            if c > 0:
                counts.setdefault(subj, {})[s] = c
    return counts

def rebuild_schedule_counts():
    global schedule_counts
    schedule_counts = [[defaultdict(lambda: defaultdict(int)) for _ in range(7)] for _ in range(6)]

    all_schedules = Schedule.query.all()
    for sched in all_schedules:
        day = sched.day
        period = sched.period
        subject = sched.subject
        slot = sched.slot
        schedule_counts[day][period][subject][slot] += 1

# 集中講義の登録人数（1枠のみ）
special_counts = [[defaultdict(int)]]

# 登録可能な科目（全体の一覧）
subjects = {  
    "情報科学科": [
                "情報理論(情科)", 
                "アルゴリズムとデータ構造",
                "デジタル信号処理(情科)", 
                "オブジェクト指向プログラミング(1)", 
                "SD_PBL(2)",
                "微分方程式論(情科)"
                "英語",
                "基礎論理回路",
                "データベースシステム"
                "オブジェクト指向プログラミング(2)",
                "ベクトル解析学(情科)",
                "コンピュータシステム"
                ],

    "知能情報工学科":[
            "プログラミング応用",
            "再・オブジェクト指向プログラミング",
            "情報理論(知能)",
            "古典制御理論",
            "微分方程式論(知能)",
            "知能情報数学入門",
            "再・データサイエンス基礎",
            "知的情報処理",
            "デジタル信号処理(知能)",
            "再・企業マネジメント",
            "SD_PBL(2)",
            "技術者倫理",
            "人間工学",
            "ベクトル解析学(知能)",
            "データサイエンス・コンピューティング応用",
            "知能情報数学基礎"
          ],

}

# 集中講義専用科目リスト
special_subjects = ["メディア表現"]

# 表示用の曜日ラベル
days = ["月", "火", "水", "木", "金", "土"]

# 時間割の開講科目（曜日×時限に対して開講している科目）
offered_subjects = {
    #月曜日
    (0, 0): ["プログラミング応用","再・オブジェクト指向プログラミング","情報理論(情科)","情報理論(知能)"],
    (0, 1): ["情報理論(情科)","古典制御理論","微分方程式論(知能)","人間工学","コンピュータシステム", "ベクトル解析学(情科)"],
    (0, 2): ["知能情報数学入門","再・データサイエンス基礎"],
    (0, 3): ["英語","ベクトル解析学(知能)","微分方程式論(情科)"],
    (0, 4): [],
    (0, 5): [],
    (0, 6): [],
    #火曜日
    (1, 0): ["アルゴリズムとデータ構造"],     
    (1, 1): ["デジタル信号処理(情科)","基礎論理回路","デジタル信号処理(知能)"],
    (1, 2): ["知的情報処理","データサイエンス・コンピューティング応用","データベースシステム"],
    (1, 3): ["オブジェクト指向プログラミング(1)","知的情報処理","データサイエンス・コンピューティング応用","ハードウェア記述言語"],
    (1, 4): ["オブジェクト指向プログラミング(1)","ハードウェア記述言語"],
    (1, 5): [],
    (1, 6): [],
    #水曜日
    (2, 0): [],
    (2, 1): ["SD_PBL(2)"],
    (2, 2): [],
    (2, 3): [],
    (2, 4): [],
    (2, 5): [],
    (2, 6): [],
    #木曜日
    (3, 0): ["プログラミング応用", "再・オブジェクト指向プログラミング","情報理論"],
    (3, 1): ["情報理論(情科)", "古典制御理論","ベクトル解析学(知能)", "人間工学","コンピュータシステム"],
    (3, 2): ["知能情報数学入門", "再・データサイエンス基礎","オブジェクト指向プログラミング(2)"],
    (3, 3): ["微分方程式論(情科)","オブジェクト指向プログラミング(2)", "ベクトル解析学(情科)"],
    (3, 4): [],
    (3, 5): [],
    (3, 6): [],
    #金曜日
    (4, 0): ["アルゴリズムとデータ構造","技術者倫理"],
    (4, 1): ["デジタル信号処理(情科)","基礎論理回路"],
    (4, 2): ["再・企業マネジメント","知能情報数学基礎","データベースシステム"],
    (4, 3): ["再・企業マネジメント","知能情報数学基礎"],
    (4, 4): [],
    (4, 5): [],
    (4, 6): [],
    #土曜日
    (5, 0): [],
    (5, 1): [],
    (5, 2): [],
    (5, 3): [],
    (5, 4): [],
    (5, 5): [],
    (5, 6): [],
    # 必要に応じて追加
}

# 6日 × 7限の時間割登録（人数カウント）
# 各枠で人数を管理（slot=1,2）
schedule_counts = [[defaultdict(lambda: defaultdict(int)) for _ in range(7)] for _ in range(6)]

color_map = {
    "情報理論(情科)": "red",
    "アルゴリズムとデータ構造": "red",
    "デジタル信号処理(情科)": "red",
    "SD_PBL(2)": "red",
}

@app.route('/timetable')
def timetable():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'user_registration' not in session:
        session['user_registration'] = {}

    # ユーザーが登録した科目を取得
    user_subjects = set(session['user_registration'].values())

    # コース選択肢を取得（デフォルトはなし）
    user_course = session.get('user_course', None)

    # コースに基づいた科目リストを選択
    available_subjects = subjects.get(user_course, [])

    return render_template(
        'index.html',
        schedule_counts=schedule_counts,
        special_counts=special_counts, 
        days=days,
        user_subjects=user_subjects,
        offered_subjects=offered_subjects,
        available_subjects=available_subjects,
        user_course=user_course,
        color_map=color_map,
        special_subjects=special_subjects
    )

@app.route('/set_course', methods=['POST'])
def set_course():
    data = request.json
    course = data['course']
    session['user_course'] = course
    return jsonify({"success": True, "course": course})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    day = int(data['day'])
    period = int(data['period'])
    subject = data['subject']
    slot = int(data.get('slot', 1))
    user_id = session['user_id']
    key = f"{day}-{period}-{slot}"

    existing = Schedule.query.filter_by(user_id=user_id, day=day, period=period, slot=slot).first()

    if not subject:
        if existing:
            prev_subject = existing.subject
            prev_slot = existing.slot
            db.session.delete(existing)
            db.session.commit()

            if prev_subject in schedule_counts[day][period]:
                schedule_counts[day][period][prev_subject][prev_slot] = max(
                    0, schedule_counts[day][period][prev_subject][prev_slot] - 1
                )

                # ✅ 登録人数が0人になったslotを削除
                if schedule_counts[day][period][prev_subject][prev_slot] == 0:
                    del schedule_counts[day][period][prev_subject][prev_slot]

                # ✅ slotがすべてなくなった場合、subjectも削除
                if not schedule_counts[day][period][prev_subject]:
                    del schedule_counts[day][period][prev_subject]

        session.pop(key, None)
        if 'user_registration' in session:
            session['user_registration'].pop(key, None)

        counts = build_counts(day, period)
        return jsonify({"success": True, "counts": counts})

    
    # 登録または更新の場合
    if existing:
        if existing.subject != subject:
            old_subject = existing.subject
            old_slot = existing.slot
            schedule_counts[day][period][old_subject][old_slot] = max(
                0, schedule_counts[day][period][old_subject][old_slot] - 1
            )

            existing.subject = subject
            db.session.commit()
    else:
        new_schedule = Schedule(day=day, period=period, slot=slot, subject=subject, user_id=user_id)
        db.session.add(new_schedule)

    # 新しい科目をカウント
    schedule_counts[day][period][subject][slot] += 1
    session[key] = subject
    session['user_registration'][key] = subject
    db.session.commit()

    # 最新の counts を返す
    counts = {}
    for subj, slots in schedule_counts[day][period].items():
        for s, c in slots.items():
            if c > 0:
                counts.setdefault(subj, {})[s] = c

    return jsonify({"success": True, "counts": counts})

@app.route('/register_special', methods=['POST'])
def register_special():
    data = request.json
    subject = data['subject']
    user_id = session['user_id']

    prev_special = SpecialSchedule.query.filter_by(user_id=user_id).first()
    prev_subject = prev_special.subject if prev_special else None

    # 以前の登録解除
    if prev_subject:
        special_counts[0][0][prev_subject] = max(0, special_counts[0][0][prev_subject] - 1)
        db.session.delete(prev_special)

    # 新しい登録
    if subject:
        if subject not in special_subjects:
            return jsonify({"success": False, "message": "無効な科目です。"})

        new_special = SpecialSchedule(subject=subject, user_id=user_id)
        db.session.add(new_special)
        special_counts[0][0][subject] += 1
        session['special'] = subject
    else:
        session.pop('special', None)

    db.session.commit()

    return jsonify({
        "success": True,
        "subject": subject,
        "count": special_counts[0][0].get(subject, 0)
    })

@app.route('/get_schedule')
def get_schedule():
    return jsonify([
        [
            {
                subject: dict(slots) for subject, slots in cell.items()
            }
            for cell in row
        ] for row in schedule_counts
    ])

@app.route('/get_special')
def get_special():

    return jsonify(special_counts[0][0])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    course = db.Column(db.String(50), nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Integer, nullable=False)
    period = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # ユーザーごとに保存
    slot = db.Column(db.Integer, nullable=False)

class SpecialSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ホームページ
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('timetable'))
  
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        course = request.form['course']

        # 同じユーザー名が登録されていないか確認
        if User.query.filter_by(username=username).first():
            return "そのユーザー名はすでに使われています", 400

        # 新しいユーザーを作成
        new_user = User(username=username, password=password, course=course)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')
     
@app.before_request
def load_user_schedule():
    if 'user_id' in session:
        user_id = session['user_id']
        session['user_registration'] = {}

        user_schedules = Schedule.query.filter_by(user_id=user_id).all()
        for sched in user_schedules:
            key = f"{sched.day}-{sched.period}-{sched.slot}"
            session[key] = sched.subject
            session['user_registration'][key] = sched.subject

        special = SpecialSchedule.query.filter_by(user_id=user_id).first()
        if special:
            session['special'] = special.subject

    rebuild_schedule_counts()

# ユーザーログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['user_course'] = user.course 
            return redirect(url_for('dashboard'))
        else:
            return "ログイン失敗", 401
    return render_template('login.html')

# ダッシュボード
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

if __name__ == '__main__':
    app.secret_key = '適当なランダム文字列'  # sessionを使うために必要
    with app.app_context():
        db.create_all()  # アプリケーションが起動する際にテーブルを作成
    app.run(debug=True)
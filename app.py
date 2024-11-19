import time
from flask import Flask, jsonify, redirect, render_template, url_for, request, flash, session, Response
from DB_handler import DBModule
import cv2
from ultralytics import YOLO
import numpy as np
import firebase_admin
from firebase_admin import credentials, db, storage
import threading
import tkinter as tk
from Fall_Detection import FallDetection
from requests.exceptions import HTTPError
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, url_for, request, flash, session, Response
from DB_handler import DBModule
import cv2
from ultralytics import YOLO
import numpy as np
import firebase_admin
from firebase_admin import credentials, db, storage
import threading
import tkinter as tk
from Fall_Detection import FallDetection
from requests.exceptions import HTTPError
from datetime import datetime
from flask_cors import CORS



# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = ""
DB = DBModule()

# Firebase 인증 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate('./serviceAccountKey.json')
    firebase_admin.initialize_app(cred, {
        'storageBucket':''  # Realtime Database 설정
    })


# Flask 라우팅 설정
@app.route("/")
def index():
    if "email" in session:
        user = session["email"]
        user_name = session["userName"]
        role = session.get("role", "User")
        print(f"User logged in: {user}")
        return render_template("index.html", user=user, role=role, userName=user_name)
    else:
        user = "Login"
        print("No user logged in")
        return render_template("index.html", user="Login", role="User")


@app.route("/login")
def login():
    if "email" in session:
        return redirect(url_for("base"))
    return render_template("login.html")



@app.route("/login_done", methods=["POST"])
def login_done():
    data = request.get_json()
    email = data.get("email")
    name = data.get("name")
    print(email)
    pwd = data.get("pwd")
    print(pwd)

    uid = DB.login(email, pwd)  # DB.login이 성공 시 uid 반환
    if uid:
        # userId와 userName을 세션에 저장
        session["userId"] = uid
        session["email"] = email
        
        # DB에서 userName을 가져오는 부분 추가 (Firebase Realtime DB를 사용한다고 가정)
        user_ref = db.reference(f'/users/{uid}')
        user_data = user_ref.get()
        user_name = user_data.get('name')
        print(user_name)
        session["userName"] = user_name

        # 역할도 세션에 저장
        session["role"] = "Admin"
        print(session["role"])

        return jsonify({"success": True, "userName": session["userName"]}), 200
    else:
        flash("올바르지 않은 계정입니다.")
        return jsonify({"success": False}), 400


@app.route("/logout")
def logout():
    if "email" in session:
        session.pop("email")
        return redirect(url_for("index"))
    else:
        return redirect(url_for("login"))


@app.route("/signin")
def signin():
    return render_template("signin.html")


@app.route("/signin_done", methods=["GET"])
def signin_done():
    email = request.args.get("email")
    pwd = request.args.get("pwd")
    name = request.args.get("name")
    
    if DB.signin(email=email, pwd=pwd, name=name):
        flash("회원가입이 완료되었습니다.")
        return redirect(url_for("login"))
    else:
        flash("이미 존재하는 이메일입니다.")
        return redirect(url_for("signin"))


# 시니어 추가 페이지 라우팅
@app.route('/add_senior')
def add_senior():
    if 'email' in session:
        return render_template('add_senior.html')  #Add_Senior.html 파일을 렌더링
    else:
        return redirect(url_for('login'))  # 로그인되지 않았다면 로그인 페이지로 리디렉션


# 메인 페이지 렌더링 (시니어 리스트 보기)
@app.route('/view_seniors')
def view_seniors():
    if 'email' in session:
        return render_template('view_senior.html')
    else:
        return redirect(url_for('login'))
    
    
#시니어 세부 정보 보기
@app.route('/senior_details/<string:senior_id>')
def senior_details(senior_id):
    try:
        senior_ref = db.reference(f'seniors/{senior_id}')
        senior = senior_ref.get()  # Firebase에서 특정 시니어 데이터 가져오기

        if not senior:
            return "Senior not found", 404

        return render_template('senior_details.html', senior=senior)
    except Exception as e:
        return f"Error retrieving senior details: {e}", 500

@app.route('/get_all_media_urls')
def get_all_media_urls():
    try:
        bucket = storage.bucket()
        blobs = bucket.list_blobs()  # 모든 파일 가져오기
        file_urls = []

        for blob in blobs:
            # 각 파일의 URL을 생성
            url = blob.generate_signed_url(timedelta(seconds=300), method='GET')
            file_urls.append({'name': blob.name, 'url': url})

        return jsonify({'files': file_urls})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/image_display')
def image_page():
    return render_template('image_display.html')

def get_notices():
    ref = db.reference('notices')
    notices = ref.get()

    # 공지사항이 없는 경우 빈 딕셔너리 반환
    if notices is None:
        return {}

    # 공지사항을 날짜 기준으로 최신순으로 정렬
    sorted_notices = dict(sorted(notices.items(), key=lambda x: x[1]['date'], reverse=True))

    return sorted_notices

@app.route('/notices')
def notice_list():
    notices = get_notices()

    return render_template('notice_list.html', post_list=notices, length=len(notices))


@app.route('/inquiries')
def inquiry_list():
    # DBModule의 메서드로 문의사항 목록 가져오기
    inquiries = DB.get_inquiries()

    if inquiries is None:
        inquiries = {}

    return render_template('inquiry_list.html', inquiry_list=inquiries, length=len(inquiries))

@app.route('/delete_inquiry/<inquiry_id>', methods=["POST"])
def delete_inquiry(inquiry_id):
    # 관리자 권한 확인
    if session.get('role') != 'Admin':
        flash('문의사항 삭제 권한이 없습니다.')
        return redirect(url_for('inquiry_list'))

    # DB에서 문의사항 삭제
    DB.delete_inquiry(inquiry_id)
    flash('문의사항이 성공적으로 삭제되었습니다.')
    return redirect(url_for('inquiry_list'))



@app.route('/inquiry/<inquiry_id>')
def inquiry_detail(inquiry_id):
    inquiry = DB.get_inquiry_by_id(inquiry_id)  # 특정 문의 사항 가져오기
    comments = DB.get_comments_by_inquiry_id(inquiry_id)  # comments/{inquiry_id}에서 댓글 가져오기
    role = session.get('role', 'User')  # 세션에서 사용자 역할 가져오기
    return render_template('inquiry_detail.html', inquiry=inquiry, comments=comments, inquiry_id=inquiry_id, role=role)


@app.route('/add_comment/<inquiry_id>', methods=["POST"])
def add_comment(inquiry_id):
    comment_content = request.form['comment_content']
    user_id = session.get('userId')
    role = session.get('role')
    user_name = session.get('userName')

    if not user_name or not user_id or not role:
        print("User details are missing in session")
        print(f"{user_name}")
        print(f"{user_id}")
        print(f"{role}")

        flash('댓글 작성 중 오류가 발생했습니다.')
        return redirect(url_for('inquiry_detail', inquiry_id=inquiry_id))

    DB.add_comment(inquiry_id, comment_content, user_id, role, user_name)
    return redirect(url_for('inquiry_detail', inquiry_id=inquiry_id))

@app.route('/delete_comment/<inquiry_id>/<comment_id>', methods=["POST"])
def delete_comment(inquiry_id, comment_id):
    # 관리자 권한 확인
    if session.get('role') != 'Admin':
        flash('댓글 삭제 권한이 없습니다.')
        return redirect(url_for('inquiry_detail', inquiry_id=inquiry_id))

    # DB에서 댓글 삭제
    DB.delete_comment(inquiry_id, comment_id)
    flash('댓글이 성공적으로 삭제되었습니다.')
    return redirect(url_for('inquiry_detail', inquiry_id=inquiry_id))


@app.route('/write', methods=['GET', 'POST'])
def write_notice():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 공지사항을 Firebase에 저장
        if DB.write_notice(title, content, date):
            flash('공지사항이 성공적으로 작성되었습니다.')
        else:
            flash('공지사항 작성 중 오류가 발생했습니다.')

        # 공지사항을 작성한 후 notices 경로로 리다이렉트
        return redirect(url_for('notice_list'))

    # GET 요청일 때 현재 날짜를 전달
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('write_notice.html', current_date=current_date)

@app.route('/delete_notice/<pid>', methods=["POST"])
def delete_notice(pid):
    # 관리자 권한 확인
    if session.get('role') != 'Admin':
        flash('공지사항 삭제 권한이 없습니다.')
        return redirect(url_for('notice_list'))

    # DB에서 공지사항 삭제
    DB.delete_notice(pid)
    flash('공지사항이 성공적으로 삭제되었습니다.')
    return redirect(url_for('notice_list'))

@app.route('/notice_detail/<pid>')
def notice_detail(pid):
    notice = DB.get_notice_by_id(pid)  # 특정 공지사항 가져오기
    role = session.get('role', 'User')  # 세션에서 사용자 역할 가져오기
    return render_template('notice_detail.html', notice=notice, pid=pid, role=role)

# CCTV 비디오 스트리밍
def gen_frames(camera):
    while camera.isOpened():
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# YOLO 처리된 비디오 스트리밍
def gen_yolo_frames(model, camera):
    while camera.isOpened():
        success, frame = camera.read()
        if not success:
            break
        else:
            results = model(frame)
            for r in results:
                annotated_frame = r.plot()
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



from multiprocessing import Process, Queue


model1 = YOLO('yolo models/yolov8n-pose.pt')
model2 = YOLO('yolo models/yolov8n-pose.pt')


@app.route("/cctv")
def cctv():
    return render_template("cctv.html")


# Firebase Admin 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate('./serviceAccountKey.json')
    firebase_admin.initialize_app(cred, {'storageBucket': 'python-firebase-practice-e4827.appspot.com'})


# 프레임 큐 생성
frame_queue1 = Queue(maxsize=5)
frame_queue2 = Queue(maxsize=5)


def capture_frames(rtsp_url, frame_queue):
    """RTSP 스트림을 열고 프레임을 공유 큐에 저장"""
    cap = cv2.VideoCapture(rtsp_url)
    while cap.isOpened():
        success, frame = cap.read()
        if success:
            if frame_queue.full():
                frame_queue.get()  # 큐가 꽉 차면 가장 오래된 프레임을 삭제
            frame_queue.put(frame)
        else:
            print(f"Error: Unable to read frame from {rtsp_url}")
            time.sleep(1)
    cap.release()


def stream_frames(frame_queue):
    """공유 큐에서 프레임을 받아 웹 스트림으로 제공"""
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def run_yolo(frame_queue, model):
    """YOLO 처리된 프레임을 제공"""
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            results = model(frame)
            for r in results:
                annotated_frame = r.plot()  # 프레임에 YOLO 결과 그리기
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def run_fall_detection(frame_queue, camera_url, camera_name, model_path, folder_to_watch, save_path):
    """FallDetection 처리"""
    detector = FallDetection(video_source=camera_url,
                             model_path=model_path,
                             folder_to_watch=folder_to_watch,
                             service_account_path='./serviceAccountKey.json',
                             save_path=save_path,
                             camera_name=camera_name,
                             gui_update_callback=None)
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            detector.process_video()  


@app.route('/video_feed1')
def video_feed1():
    return Response(stream_frames(frame_queue1), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed2')
def video_feed2():
    return Response(stream_frames(frame_queue2), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/yolo_feed1')
def yolo_feed1():
    return Response(run_yolo(frame_queue1, model1), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/yolo_feed2')
def yolo_feed2():
    return Response(run_yolo(frame_queue2, model2), mimetype='multipart/x-mixed-replace; boundary=frame')


from flask_socketio import SocketIO

socketio = SocketIO(app)

@app.route('/trigger_alert', methods=['POST'])
def trigger_alert():
    socketio.emit('fall_alert', {'message': '낙상 감지가 되었다'})
    return '', 204

if __name__ == "__main__":
    
    process1 = Process(target=capture_frames, args=('./test.mp4', frame_queue1))
    process2 = Process(target=capture_frames, args=('./test.mp4', frame_queue2))

    
    # Fall detection 스레드 시작
    fall_detection_process1 = Process(target=run_fall_detection, args=(frame_queue1, './test.mp4', "Room 1",'yolo models/yolov8n-pose.pt', './cctv1','./cctv1'))
    fall_detection_process2 = Process(target=run_fall_detection, args=(frame_queue2, './test.mp4', "Room 2",'yolo models/yolov8n-pose.pt', './cctv2','./cctv2'))

   
    process1.start()
    process2.start()
    time.sleep(5)
    fall_detection_process1.start()
    fall_detection_process2.start()

    
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

    process1.join()
    process2.join()
    fall_detection_process1.join()
    fall_detection_process2.join()




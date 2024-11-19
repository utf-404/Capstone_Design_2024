import pyrebase
import json
from requests.exceptions import HTTPError
import firebase_admin
from firebase_admin import credentials, db, storage
import uuid
from datetime import datetime

class DBModule:
    def __init__(self):
        with open("./auth/firebaseAuth.json") as f:
            config = json.load(f)
        
        firebase = pyrebase.initialize_app(config)
        self.db = firebase.database()
        self.auth = firebase.auth()
        self.user = None
        

    def login(self, email, pwd):
        try:
            # 로그인 시도
            user = self.auth.sign_in_with_email_and_password(email, pwd)
            uid = user['localId']  # UID 가져오기
            return uid  # 로그인 성공 시 UID 반환
        except HTTPError as e:
            print(f"Login failed: {e}")
            return False

    def signin(self, email, pwd, name):
        try:
            # 이메일과 비밀번호로 회원가입
            user = self.auth.create_user_with_email_and_password(email, pwd)
            uid = user['localId']  # UID 가져오기
            
            # 데이터베이스에 사용자 정보 저장
            self.db.child("users").child(uid).set({
                "email": email,
                "uname": name,
                "role": "Admin"  # 기본적으로 Admin 역할로 설정
            })
            return uid  # 성공 시 UID 반환
        except HTTPError as e:
            print(f"Sign up failed: {e}")
            return False


    def DB_eventInsert(self, time, color):
        try:
            # 이벤트 발생시 timestamp와 color을 Realtime Database에 Insert
            user = self.auth.current_user
            id_token = user['idToken']
            
            ref = self.db.child("event")  # self.db를 사용하여 Firebase Realtime Database에 접근

            new_event_data = {
                'color': color,
                'time': time
            }

            print("Pushing data to Firebase========================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================")
            ref.child(str(time)).set(new_event_data, id_token)
            print(f"Event data inserted into database: ============================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================{new_event_data}")
            return True
        except Exception as e:
            print(f"DB event insert error:============================================================================================================================================================================================================================================================================================================================================================================================================================================================================================ {e}")
            return False
        
    
    #시니어 등록    
    def add_senior(self, seniorID, careFacilityID, roomID, caregiverID, name, birthDate, gender, admissionDate, existingConditions):
        try:
            # 데이터 저장
            senior_data = {
                "seniorID": seniorID,
                "careFacilityID": careFacilityID,
                "roomID": roomID,
                "caregiverID": caregiverID,
                "name": name,
                "birthDate": birthDate,
                "gender": gender,
                "admissionDate": admissionDate,
                "existingConditions": existingConditions
            }
            
            # 파이어베이스 저장
            self.db.child("seniors").child(seniorID).set(senior_data)
            print(f"Senior {seniorID} successfully added.")
            return True
        except Exception as e:
            print("Failed to add senior:", e)
            return False
        
     
    # 시니어 목록 가져오기 함수
    def get_all_seniors(self, id_token):
        try:
            # 전달된 id_token을 사용하여 Firebase 데이터 요청
            seniors = self.db.child("seniors").get(id_token)  # idToken을 통해 인증된 요청
            if seniors.val():
                return seniors.val()
            else:
                print("No seniors data found.")
                return None
        except Exception as e:
            print(f"Error fetching seniors: {e}")
            return None

    # 특정 시니어의 세부 정보 가져오기 함수
    def get_all_seniors(self):
        try:
            # 인증된 idToken으로 데이터 접근
            token = session.get("idToken")
            seniors = self.db.child("seniors").get(token)  # 인증 토큰과 함께 데이터를 요청
            if seniors.val():
                return seniors.val()
            else:
                print("No seniors data found.")
                return None
        except Exception as e:
            print(f"Error fetching seniors: {e}")
            return None
    

    def write_notice(self, title, content, date):
        try:
            # 공지사항을 저장할 경로 설정 (notices 하위에 추가)
            ref = db.reference('notices')
            
            # 새로운 공지사항 데이터를 생성하고 푸시
            new_notice_ref = ref.push({
                'title': title,
                'content': content,
                'date': date
            })
            
            print(f"공지사항이 성공적으로 저장되었습니다: {new_notice_ref.key}")
            return True
        except Exception as e:
            print(f"공지사항 저장 중 오류가 발생했습니다: {e}")
            return False

    def delete_notice(self, pid):
        try:
            # Firebase에서 공지사항 삭제 (notices/{pid})
            ref = db.reference(f'notices/{pid}')
            ref.delete()
            print(f"Notice {pid} deleted successfully.")
        except Exception as e:
            print(f"Error deleting notice: {e}")
    def get_inquiries(self):
        ref = db.reference('inquiries')
        inquiries = ref.get()
        return inquiries

    def get_notice_by_id(self, pid):
        try:
            # Firebase에서 특정 공지사항 가져오기 (notices/{pid})
            ref = db.reference(f'notices/{pid}')
            notice = ref.get()
            if notice:
                print(f"Notice {pid} retrieved successfully.")
            else:
                print(f"No notice found with ID: {pid}")
            return notice
        except Exception as e:
            print(f"Error retrieving notice: {e}")
            return None
        
    def inquiries_list(self):
        if not self.user:
            print("User not logged in.")
            return None
        
        id_token = self.user['idToken']
        inquiries_list = self.db.child("inquiries").get(id_token).val()
        return inquiries_list

    def delete_inquiry(self, inquiry_id):
        try:
            # 1. Firebase에서 해당 문의사항 삭제 (inquiries/{inquiry_id})
            inquiry_ref = db.reference(f'inquiries/{inquiry_id}')
            inquiry_ref.delete()

            # 2. Firebase에서 해당 문의사항의 댓글 삭제 (comments/{inquiry_id})
            comments_ref = db.reference(f'comments/{inquiry_id}')
            comments_ref.delete()

            print(f"Inquiry {inquiry_id} and its comments deleted successfully.")
        except Exception as e:
            print(f"Error deleting inquiry or comments: {e}")
            
    def get_inquiry_by_id(self, inquiry_id):
        ref = db.reference(f'inquiries/{inquiry_id}')
        inquiry = ref.get()
        return inquiry
    
    def get_comments_by_inquiry_id(self, inquiry_id):
        ref = db.reference(f'comments/{inquiry_id}')
        comments = ref.get()
        return comments if comments else {}

    
    def add_comment(self, inquiry_id, comment_content, user_id, role, user_name):
        try:
            comment_id = str(uuid.uuid4())[:12]  # 고유한 comment_id 생성
            comment_data = {
                "content": comment_content,
                "userId": user_id,
                "role": role,
                "userName": user_name  # 작성자 이름 저장
            }

            # Firebase에 댓글 저장 (comments/{inquiry_id}/{comment_id})
            ref = db.reference(f'comments/{inquiry_id}')
            ref.child(comment_id).set(comment_data)
            print(f"Comment added successfully: {comment_data}")  # 로그 출력
        except Exception as e:
            print(f"Error adding comment to Firebase: {e}")  # 에러 발생 시 로그 출력

    def delete_comment(self, inquiry_id, comment_id):
        try:
            # Firebase에서 해당 댓글 삭제 (comments/{inquiry_id}/{comment_id})
            ref = db.reference(f'comments/{inquiry_id}/{comment_id}')
            ref.delete()
            print(f"Comment {comment_id} deleted successfully.")
        except Exception as e:
            print(f"Error deleting comment: {e}")

    def post_detail(self, pid):
        # 게시글 정보 가져오기
        post = self.db.child("posts").child(pid).get().val()

        # 댓글 데이터가 있는지 확인
        comments = self.db.child("posts").child(pid).child("comments").get().val()

        # 게시글에 pid 추가
        if post is not None:
            post["pid"] = pid

        # 댓글이 있으면 추가, 없으면 빈 리스트로 설정
        post["comments"] = comments if comments else {}

        return post

    def delete_post(self, pid):
        self.db.child("posts").child(pid).remove()

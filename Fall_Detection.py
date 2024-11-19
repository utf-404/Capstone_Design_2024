import os
import time
import numpy as np
import cv2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ultralytics import YOLO
from copy import deepcopy
from datetime import datetime
from DB_handler import DBModule  # DBModule 클래스 임포트
from fcm_topic import FCMNotificationSender
import firebase_admin
from firebase_admin import credentials, storage
import tempfile
from flask import session
import requests


class FallDetection(FileSystemEventHandler):
    def __init__(self, model_path, video_source, folder_to_watch, service_account_path, save_path, camera_name, gui_update_callback=None):
        self._init_firebase()
        # Fall detection initialization
        self.camera_name = camera_name
        self.model = YOLO(model_path)
        self.safe_count = 0
        self.fallen_count = 0
        self.previous_y_values = None
        self.first_point_threshold = None
        self.second_point_threshold = None
        self.falling_threshold = None
        self.fallen_state = False
        self.MIN_ELAPSED_TIME_THRESHOLD = 5
        self.fall_start_time = None
        self.elapsed_time_states = []
        self.fall_alerted = False
        self.video_frames_before = []
        self.frozen_video_frames_before = []
        self.video_frames_after = []
        self.taking_video = False
        self.clip_frames = []
        self.save_path = save_path
        self.VIDEO_FPS = 10
        self.results = self.model(source=video_source, show=False, conf=0.3, stream=True, save=False)
        self.bucket = storage.bucket()
        self.gui_update_callback = gui_update_callback  # GUI 업데이트 콜백 함수

        # Color detection initialization
        self.color_info = {}
        self.folder_to_watch = folder_to_watch
        self.observer = Observer()
        self.observer.schedule(self, self.folder_to_watch, recursive=False)
        self.observer.start()

        # notification initialization
        self.notification_sender = FCMNotificationSender(service_account_path)

        # DB handler initialization
        self.db_handler = DBModule()
        if self.db_handler:
            print("DB handler object created successfully.")
            if self.db_handler.login('admin3@gmail.com', '123456'):
                print("Login successful.")
            else:
                print("Login failed")
        else:
            print("Failed to create DB handler object.")

    def _init_firebase(self):
        # Firebase 인증 및 앱 초기화
        if not firebase_admin._apps:
            cred = credentials.Certificate('./serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {'storageBucket': 'appproject-739aa.appspot.com'})

        self.bucket = storage.bucket()

    def upload_to_firebase(self, file_path):
        try:
            blob = self.bucket.blob(file_path.split('/')[-1])
            blob.upload_from_filename(file_path)
            print(f"Uploaded {file_path} to Firebase Storage.")
        except Exception as e:
            print(f"Failed to upload {file_path} to Firebase Storage: {e}")

    def upload_test_file_to_firebase(self):
        # 테스트 파일 생성
        test_file_path = 'test_upload.txt'
        with open(test_file_path, 'w') as f:
            f.write("Firebase Storage 연동 테스트 파일입니다.")

        # 파일 업로드
        self.upload_to_firebase(test_file_path)
        print(f"Uploaded {test_file_path} to Firebase Storage.")


    def save_cropped_image(self, r):
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        boxes = r.boxes.xyxy.cpu().numpy()
        if len(boxes) > 0:
            x_min, y_min, x_max, y_max = boxes[0]
            x_min, y_min, x_max, y_max = int(x_min), int(y_min), int(x_max), int(y_max)
            cropped_img = r.orig_img[y_min:y_max, x_min:x_max]
            img_save_path = os.path.join(self.save_path, f'fallen_frame_{current_time}.png')
            cv2.imwrite(img_save_path, cropped_img)
            print(f'Fallen state detected. Image saved as {img_save_path}')
            self.upload_to_firebase(img_save_path)

    def frame_coordinates(self, frame):
    # 각 프레임에서 keypoint의 y 좌표를 추출
        y_values_frame = [keypoint[1].cpu().numpy() for keypoint in frame.keypoints.xy[0] if keypoint[1].cpu().numpy() != 0]
        return y_values_frame

    def get_starting_frames(self, results):
        start_time = time.time()
        first_frame = next(results, None)
        if first_frame is not None:
            y_values_first_frame = self.frame_coordinates(first_frame)
            while(len(y_values_first_frame) < 6):
                first_frame = next(results, None)
                y_values_first_frame = self.frame_coordinates(first_frame)
            self.falling_threshold = ((y_values_first_frame[len(y_values_first_frame)-1] - y_values_first_frame[0]) * 3/4) + 20
            
        print("Falling threshold:", self.falling_threshold)
        second_frame = next(results, None)
        if second_frame is not None:
            y_values_second_frame = self.frame_coordinates(second_frame)
            while(len(y_values_second_frame) < 6):
                second_frame = next(results, None)
                y_values_second_frame = self.frame_coordinates(second_frame)
    
        first_point_diff = abs(y_values_first_frame[0] - y_values_second_frame[0])
        second_point_diff = abs(y_values_first_frame[5] - y_values_second_frame[5])
        self.first_point_threshold = first_point_diff + 15
        self.second_point_threshold = second_point_diff + 15

        print("First point threshold:", self.first_point_threshold)
        print("Second point threshold:", self.second_point_threshold)

        return self.first_point_threshold, self.second_point_threshold, start_time   

    def check_falling(self, y_values, r):
        if self.previous_y_values is not None and len(y_values) >= 6 and len(self.previous_y_values) >= 6:
            first_point_diff = abs(self.previous_y_values[0] - y_values[0])
            second_point_diff = abs(self.previous_y_values[5] - y_values[5])

            if (self.falling_threshold is not None) and (self.maximum - self.minimum <= self.falling_threshold):
                if (first_point_diff <= self.first_point_threshold) and (second_point_diff <= self.second_point_threshold):
                    print("Laying down")
                    if self.fallen_state:
                        self.elapsed_time_states.append("Laying down")
                        self.fall_start_time, self.elapsed_time_states = self.check_falling_time(self.fall_start_time, self.elapsed_time_states,r)
                    else:
                        self.fall_start_time = None
                else:
                    if self.fallen_state:
                        self.elapsed_time_states.append("Fallen")
                        self.fall_start_time, self.elapsed_time_states = self.check_falling_time(self.fall_start_time, self.elapsed_time_states,r)
                        print("Fallen")
                        print("states:", self.elapsed_time_states)
                    else:
                        self.fallen_state = True
                        self.taking_video = True
                        print("Taking video set to True")
                        self.fall_start_time = time.time()
                        self.elapsed_time_states.append("Fallen")
                        print("Fallen")
                        print("STARTING TIME OF FALL:", self.fall_start_time)
                        print("states:", self.elapsed_time_states)
            else:
                if self.fall_alerted:
                    self.taking_video = True
                else:
                # If they're just safe and stood up before the 10 seconds, then reset
                    self.fallen_state = False
                    self.taking_video = False
                    self.frozen_video_frames_before.clear()
                    self.video_frames_after.clear()
                
                self.fall_start_time = None
                self.elapsed_time_states.clear()
                print("Safe")
        
        self.previous_y_values = y_values

    def check_falling_time(self, fall_start_time, elapsed_time_states,r):
        if fall_start_time is not None:
            duration_of_fall = time.time() - fall_start_time
            print("Duration of fall:", duration_of_fall)
            if duration_of_fall >= self.MIN_ELAPSED_TIME_THRESHOLD:
                print("FALL ALERT!!")
                self.fall_alerted = True
                self.taking_video = True
                if self.camera_name == "Room 1":
                    self.save_cropped_image(r)
                    self.save_video_clip()
                    print("Fall detected in Room 1 - Video saved.")
                elif self.camera_name == "Room 2":
                    self.save_cropped_image(r)
                    self.save_video_clip()
                    print("Fall detected in Room 2 - Video saved.")
                
                try:
                    requests.post("http://localhost:5000/trigger_alert")
                except requests.ConnectionError as e:
                    print(f"Error sending alert: {e}")

                
                time.sleep(2)
                self.fall_start_time = None
                self.elapsed_time_states.clear()
                self.fallen_state = False
                self.reset_fall_state()
                
                
        return fall_start_time, elapsed_time_states
    
    def reset_session_alert(self):
        """경고를 보낸 후 세션에서 상태를 초기화하는 함수"""
        session['fall_alert'] = False


    def check_falling_time_out_of_frame(self, fall_start_time, elapsed_time_states, r):
        if fall_start_time is not None:
            duration_of_fall = time.time() - fall_start_time
            print("Duration of fall:", duration_of_fall)
            if duration_of_fall >= self.MIN_ELAPSED_TIME_THRESHOLD:
                print("Elapsed time states:", elapsed_time_states)
                print("FALL ALERT!!!")
                while len(self.video_frames_after) <= 150:
                    self.video_frames_after.append(r.orig_img)
                if self.camera_name == "Room 1":
                    self.save_video_clip()
                    print("Time out - Fall detected in Room 1")
                    self.save_cropped_image(r)
                elif self.camera_name == "Room 2":
                    self.save_video_clip()
                    print("Time out - Fall detected in Room 2")
                    self.save_cropped_image(r)

                try:
                    requests.post("http://localhost:5000/trigger_alert")
                except requests.ConnectionError as e:
                    print(f"Error sending alert: {e}")
                time.sleep(2)
                self.taking_video = False
                self.video_frames_before.clear()
                self.video_frames_after.clear()
                self.frozen_video_frames_before.clear()
                self.fall_start_time = None
                self.elapsed_time_states.clear()
                self.fallen_state = False

                self.reset_fall_state()
                

        return fall_start_time, elapsed_time_states

    def save_video_clip(self):
        self.clip_frames = self.frozen_video_frames_before + self.video_frames_after

        if not self.clip_frames:
            print("No frames to save.")
            return
        
        print(f"Number of frames in clip: {len(self.clip_frames)}")
         
        output_dir = r"C:\Users\User\Desktop\server\static\video"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)  # 폴더가 없으면 생성

    # 파일 이름을 포함한 전체 경로
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = os.path.join(output_dir, f"fallen_clip_{timestamp}.mp4")

        out = cv2.VideoWriter(temp_file_path, cv2.VideoWriter_fourcc(*'mp4v'), self.VIDEO_FPS, (self.clip_frames[0].shape[1], self.clip_frames[0].shape[0]))
        
        for frame in self.clip_frames:
            out.write(frame)
        out.release()
        print("Saved video clip:", temp_file_path)
        try:
            self.upload_to_firebase(temp_file_path)
        except Exception as e:
            print(f"Failed to upload {temp_file_path} to Firebase Storage: {e}")


    def reset_fall_state(self):
        self.fallen_state = False
        self.fall_alerted = False
        self.taking_video = False
        self.video_frames_before.clear()
        self.video_frames_after.clear()
        self.frozen_video_frames_before.clear()
        self.fall_start_time = None
        self.elapsed_time_states.clear()

    def process_video(self):
        # Firebase Storage 연동 테스트 실행
        self.upload_test_file_to_firebase()
        print("Processing video started")  # 로그를 출력하여 시작을 알림
        # 기존 코드 계속 실행...
        
        if self.results:
            self.first_point_threshold, self.second_point_threshold,start_time = self.get_starting_frames(self.results)
            for r in self.results:
                if time.time() - start_time > 5 and not self.fallen_state:
                    self.first_point_threshold, self.second_point_threshold,start_time = self.get_starting_frames(self.results)

                if len(self.video_frames_before) > 100:
                    self.video_frames_before.pop(0)
                else:
                    self.video_frames_before.append(r.orig_img) 
                
                print(f"self.taking_video: {self.taking_video}")
                print(f"Frames before length: {len(self.video_frames_before)}")
                print(f"Frozen frames before length: {len(self.frozen_video_frames_before)}")
                print(f"Frames after length: {len(self.video_frames_after)}")    
                    
                if self.taking_video:
                    if (len(self.frozen_video_frames_before) == 0):
                        self.frozen_video_frames_before = deepcopy(self.video_frames_before)
                    if len(self.video_frames_after) <= 150:
                        self.video_frames_after.append(r.orig_img)
                    else:
                        #self.save_video_clip()
                        time.sleep(2)
                        self.taking_video = False
                        self.video_frames_before.clear()
                        self.video_frames_after.clear()
                        self.frozen_video_frames_before.clear()
                        self.fall_start_time = None
                        self.elapsed_time_states.clear()
                        self.fallen_state = False
                else:
                    if len(self.video_frames_before) > 100:
                        self.video_frames_before.pop(0)
                    else:
                        self.video_frames_before.append(r.orig_img)

                y_values = self.frame_coordinates(r)

                if len(y_values) >= 6:
                    self.minimum = min(y_values)
                    self.maximum = max(y_values) 
                    self.check_falling(y_values, r)
                else:
                    if self.fallen_state == True:
                        self.elapsed_time_states.append("No human detected")
                        self.fall_start_time, self.elapsed_time_states = self.check_falling_time_out_of_frame(self.fall_start_time, self.elapsed_time_states,r)
                        print("No human detected.")
                        print("states:", self.elapsed_time_states)
                
                

        
        cv2.destroyAllWindows()


    # Color detection methods
    def on_created(self, event):
        if event.is_directory:
            return None
        elif event.event_type == 'created':
            print(f"File created: {event.src_path}")
            self.process_image(event.src_path)

    def process_image(self, path):
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return None  # 파일이 존재하지 않으면 None 반환
        
        # 파일 접근 권한 문제를 처리하기 위한 대기 및 재시도
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                img = cv2.imread(path)
                if img is None:
                    print(f"Failed to read the image. Skipping file: {path}")
                    return None  # 이미지 읽기에 실패하면 None 반환
                break
            except PermissionError:
                print(f"Attempt {attempt + 1} of {max_attempts}: Permission denied for file {path}. Retrying...")
                time.sleep(1)
        else:
            print(f"Failed to open the file after {max_attempts} attempts: {path}")
            return None  # 최대 시도 횟수를 넘으면 None 반환

        # 파일 생성 시간 가져오기
        file_creation_time = time.ctime(os.path.getctime(path))

        # 색상 범위 설정
        color_ranges = {
            "red": [
                (np.array([0, 100, 100], dtype="uint8"), np.array([10, 255, 255], dtype="uint8")),
                (np.array([160, 100, 100], dtype="uint8"), np.array([179, 255, 255], dtype="uint8"))
            ],
            "blue": [
                (np.array([100, 100, 100], dtype="uint8"), np.array([140, 255, 255], dtype="uint8"))
            ],
            "green": [
                (np.array([40, 100, 100], dtype="uint8"), np.array([70, 255, 255], dtype="uint8"))
            ]
        }
        threshold = 0.05
        print(f"Processing image: {path}")

        color_ids={
            "red": 1,
            "green": 2,
            "blue": 3
        }
        color_found = False
        detected_colors = []
        detected_color_id = None

        # 색상 감지
        for color_name, bounds in color_ranges.items():
            lower_bounds, upper_bounds = zip(*bounds)
            result, mask = self.detect_color(img, lower_bounds, upper_bounds)
            color_proportion = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])
            if color_proportion > threshold:
                detected_colors.append((color_name, color_proportion))
                print(f"Detected {color_name} with proportion {round(color_proportion, 2)} in {path}")
                color_found = True
            else:
                print("detected")

        for color_name, _ in detected_colors:
            detected_color_id = color_ids.get(color_name)
            if detected_color_id == 1: #red
                self.notification_sender.send_topic_notification(f"admin", f"긴급: 요양환자 낙상 ({self.camera_name})", "Red 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.notification_sender.send_topic_notification(f"1", f"긴급: 요양환자 낙상 ({self.camera_name})", "Red 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.db_handler.DB_eventInsert(file_creation_time, color_name)
            elif detected_color_id == 2: # green
                self.notification_sender.send_topic_notification(f"admin", f"긴급: 요양환자 낙상 ({self.camera_name})", "Green 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.notification_sender.send_topic_notification(f"2", f"긴급: 요양환자 낙상 ({self.camera_name})", "Green 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.db_handler.DB_eventInsert(file_creation_time, color_name)
            elif detected_color_id == 3: # blue
                self.notification_sender.send_topic_notification(f"admin", f"긴급: 요양환자 낙상 ({self.camera_name})", "Blue 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.notification_sender.send_topic_notification(f"3", f"긴급: 요양환자 낙상 ({self.camera_name})", "Blue 색상 옷을 입은 요양환자가 낙상하였습니다.")
                self.db_handler.DB_eventInsert(file_creation_time, color_name)
            else:
                self.notification_sender.send_topic_notification(f"admin", f"긴급: 요양환자 낙상({self.camera_name})", "요양환자의 낙상이 감지되었습니다.")
                self.db_handler.DB_eventInsert(file_creation_time, "Undefined")
        if not color_found:
            detected_colors.append(("Undefined", 0))
            print(f"No significant color detected in {path}, marked as Undefined.")
            self.notification_sender.send_topic_notification(f"admin", f"긴급: 요양환자 낙상({self.camera_name})", "요양환자의 낙상이 감지되었습니다.")
            self.db_handler.DB_eventInsert(file_creation_time, "Undefined")
        self.color_info[file_creation_time] = detected_colors
        print("\nCurrent color_info dictionary:")
        print(self.color_info)

            # GUI 업데이트를 위한 콜백 호출
        if self.gui_update_callback:
            color_info_str = f"File: {path}\nCreation Time: {file_creation_time}\nColors: {self.color_info[file_creation_time]}\n"
            self.gui_update_callback(color_info_str)

        return detected_colors  # 감지된 색상 정보 반환

    def detect_color(self, img, lower_bounds, upper_bounds):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        masks = [cv2.inRange(hsv, lower, upper) for lower, upper in zip(lower_bounds, upper_bounds)]
        mask = np.bitwise_or.reduce(masks)
        result = cv2.bitwise_and(img, img, mask=mask)
        return result, mask
    

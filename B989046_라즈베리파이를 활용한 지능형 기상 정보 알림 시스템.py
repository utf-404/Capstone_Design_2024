import cv2
import requests
from bs4 import BeautifulSoup
import tkinter as tk
import tkinter.font
from datetime import datetime
import os
import threading
import RPi.GPIO as GPIO
import time
import sys

# 현재 파일의 경로
current_dir = os.path.dirname(os.path.realpath(__file__))
url = 'https://m.search.naver.com/search.naver?query=조치원+날씨'  # 날씨 정보 URL

# 사용할 GPIO 핀의 번호를 설정
button_pin = 15

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)  # 핀모드 설정
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # 버튼 핀의 입력설정 , PULL DOWN 설정

# 두 번째 창을 저장할 전역 변수
second_window = None
input_timer = None
INACTIVITY_LIMIT = 180000 # 3분(180,000밀리초)

# 캐시된 날씨 데이터
cached_weather_data = None
addinfo_display = ""  # 추가 정보 저장 변수

# Tkinter 창 띄우기 및 닫기 함수
def toggle_second_window():
    global second_window, cached_weather_data
   
    if cached_weather_data is None:
        return  # 데이터가 없으면 리턴
   
    if second_window is None or not second_window.winfo_exists():
        weatherTime = cached_weather_data.find_all('li', {'class': '_li'})
       
        title = "시간대 별 날씨 정보"
        text_1 = [weather.text.strip() for weather in weatherTime][:12]
        text_1 = "\n".join(text_1)

        text_2 = [weather.text.strip() for weather in weatherTime][12:24]
        text_2 = "\n".join(text_2)
       
        text_blank = title + "\n"+"|\n"*15

        second_window = tk.Toplevel(window)
        second_window.title("시간대 별 날씨 정보")
        second_window.geometry("640x480+100+100")  # 창 위치 지정
        second_window.resizable(False, False)

        frame = tk.Frame(second_window)
        frame.pack(expand=True, fill=tk.BOTH)

        label_1 = tk.Label(frame, text=text_1, font=tk.font.Font(size=18))
        label_1.grid(row=0, column=0, sticky=tk.W)
       
        label = tk.Label(frame, text=text_blank, font=tk.font.Font(size=14))
        label.grid(row=0, column=1, columnspan=1, sticky=tk.NS)

        label_2 = tk.Label(frame, text=text_2, font=tk.font.Font(size=18))
        label_2.grid(row=0, column=2, sticky=tk.E)
        
        label_second_info = tk.Label(frame, text="원래 창으로 돌아가려면 스위치를 눌러주세요!", font=tk.font.Font(size=8))
        label_second_info.grid(row=1, column=1, columnspan=1, sticky=tk.NS)
       
        frame.grid_columnconfigure(1, weight=1)

    else:
        second_window.destroy()
        second_window = None

    reset_timer()  # 타이머 리셋

def reset_face_detection():
    global input_timer, window
   
    # 기존 타이머 취소
    if input_timer:
        window.after_cancel(input_timer)
       
    # 모든 창 닫기
    if window:
        window.destroy()
        window_add.destroy()
   
    # 얼굴 인식 다시 시작
    threading.Thread(target=detect_faces_and_display_weather, daemon=True).start()

def detect_button_press():
    while True:
        if GPIO.input(button_pin) == GPIO.HIGH:
            print("Button pushed!")
            window.after(0, toggle_second_window)  # 메인 쓰레드에서 Tkinter 함수를 호출
            reset_timer()  # 타이머 리셋
            time.sleep(0.5)  # 버튼이 눌린 상태를 반영하고 나서 지연 시간 추가
        time.sleep(0.1)

def tick1Min():
    global cached_weather_data, addinfo_display
    html = requests.get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    cached_weather_data = soup  # 데이터 캐시
   
    address = soup.find('span', {'class': 'select_txt'}).text
    weather_data = soup.find('div', {'class': 'weather_info'})
    temperature = weather_data.find('div', {'class': 'temperature_text'}).text.strip()[5:]
    weatherStatus = weather_data.find('span', {'class': 'weather before_slash'}).text
    air = soup.find('ul', {'class': 'today_chart_list'})
    infos = air.find_all('li', {'class': 'item_today'})
    weatheraddinfo = weather_data.find('dl', {'class' : 'summary_list'}).text
    weatherTime = soup.find_all('li', {'class': '_li'})
    weather_comment=""
    add_comment=""
   
    # 요약 정보를 포함하는 p 태그를 찾음
    summary_tag = soup.find('p', {'class': 'summary'})

    # "어제보다" 텍스트를 추출
    yesterday_text = summary_tag.contents[0].strip()

    # 온도 변화를 나타내는 span 태그를 찾음
    temperature_span = summary_tag.find('span', {'class': ['temperature down', 'temperature up', 'temperature same']})

    if temperature_span:
        # 온도 변화를 나타내는 텍스트를 추출 (ex: "3.3")
        temperature_text = temperature_span.contents[0].strip()

        # 상태 텍스트 추출 (ex: "낮아요", "높아요", "같아요")
        blind_text = temperature_span.find('span', {'class': 'blind'}).text

        # 최종 결과 결합
        addinfo_display = f"{yesterday_text} {temperature_text} {blind_text}\n {weatheraddinfo}"
       
    else:
        addinfo_display = "Temperature information not found."

    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    global image
   
    image_sort = weatherStatus
    if image_sort == "맑음" and '일출' in infos[3].text:
        image_sort = image_sort + "(밤)"
    elif image_sort == "맑음" and '일몰' in infos[3].text:
        image_sort = image_sort + "(낮)"
    elif image_sort == "소나기":
        image_sort="비"
    image_path = os.path.join(current_dir, f"{image_sort}.PNG")
   
    if not os.path.exists(image_path):
        image_path = os.path.join(current_dir, "No_Data_For_Weather.PNG")
    image = tk.PhotoImage(file=image_path)

    etc = [info.text.strip() for info in infos]    
   
    display = f"현재시간: {current_time}\nLocation: {address}\nTemperature: {temperature}\nWeatherStatus: {weatherStatus}\n"
    etc_display = "|| ".join(etc)
   
        
    if any(condition in weatherStatus for condition in ["비", "눈"]):
        weather_comment = "날씨에 유의하여 우산을 챙기십시오."
    elif "황사" in weatherStatus:
        weather_comment = "황사가 발생하고 있습니다. 마스크를 착용하고 외출을 자제하세요."
    elif "번개" in weatherStatus:
        weather_comment = "번개가 발생하고 있습니다. 외출 시 주의하세요."
    elif "안개" in weatherStatus:
        weather_comment = "안개가 짙게 끼었습니다. 운전 시 주의하세요."
    elif "우박" in weatherStatus:
        weather_comment = "우박이 떨어지고 있습니다. 안전한 장소로 이동하세요."
    elif "뇌우" in weatherStatus:
        weather_comment = "뇌우가 발생하고 있습니다. 외출 시 주의하세요."
    else:
        weather_comment = "현재 날씨는 맑습니다. 좋은 하루 되세요."

    if etc[0][5:] != "좋음" or etc[1][6:] != "좋음":
        add_comment+="미세먼지에 유의하여 KF80 이상의 마스크를 챙기십시오.\n"
    if etc[2][5:] != "좋음" and '일몰' in infos[3].text:
        add_comment+="자외선에 유의하여 자외선 차단제를 바르십시오.\n"
        
    weather_forecasts = [
        ("비", "앞으로 12시간 내 비가 예상됩니다. 우산을 챙기세요."),
        ("소나기", "앞으로 12시간 내 비가 예상됩니다. 우산을 챙기세요."),
        ("눈", "앞으로 12시간 내 눈이 예상됩니다. 따뜻하게 입으세요."),
        ("황사", "앞으로 12시간 내 황사가 예상됩니다. 마스크를 착용하세요."),
        ("번개", "앞으로 12시간 내 번개가 예상됩니다. 외출 시 주의하세요."),
        ("뇌우", "앞으로 12시간 내 뇌우가 예상됩니다. 외출 시 주의하세요."),
        ("안개", "앞으로 12시간 내 안개가 예상됩니다. 운전 시 주의하세요."),
        ("우박", "앞으로 12시간 내 우박이 예상됩니다. 안전한 장소로 이동하세요.")
    ]

    forecasts = []
    for condition, message in weather_forecasts:
        if any(condition in weather.text for weather in weatherTime[:12]):
            forecasts.append(message)
            
    # 모든 조건이 False인 경우
    if not forecasts:
        forecasts.append("앞으로 12시간 동안 맑습니다.")

    # forecasts 리스트에 포함된 멘트 출력
    for forecast in forecasts:
        add_comment += forecast +"\n"

    label.config(text=display)
    label_addinfo.config(text=addinfo_display)
    label_etc.config(text=etc_display)
    label_img.config(image=image)
    label_comment.config(text=weather_comment)
    label_addcomment.config(text=add_comment)
   
    window.after(60000, tick1Min)

def detect_faces_and_display_weather():
    camera = cv2.VideoCapture(-1)
    camera.set(3, 640)
    camera.set(4, 480)

    xml = 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(xml)

    cv2.namedWindow('result')  # OpenCV 창 이름 설정
    cv2.moveWindow('result', 100, 100)  # OpenCV 창 위치 지정

    while camera.isOpened():
        _, image = camera.read()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 검출 매개변수 조정
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=10, minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE)
        print("faces detected Number: " + str(len(faces)))
       
        if len(faces):
            camera.release()
            cv2.destroyAllWindows()
            show_weather()
            break
       
        cv2.imshow('result', image)
       
        key = cv2.waitKey(1)
        if key == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

def show_weather():
    global window, window_add, label, label_img, label_etc, label_addinfo, label_comment, label_addcomment

    window = tk.Tk()
    window.title("현재 날씨 정보")
    window.geometry("640x480+100+100")  # 창 위치 지정
    window.resizable(False, False)
   
    window_add = tk.Tk()
    window_add.title("추가 정보")
    window_add.geometry("400x240+750+100")  # 창 위치 지정

   
    font = tk.font.Font(size=15)
    font_comment = tk.font.Font(size=25)
    font_info = tk.font.Font(size=8)

    label = tk.Label(window, text="", font=font)
    label.pack()

    label_img = tk.Label(window, image="")
    label_img.pack()
   
    label_addinfo = tk.Label(window, text="", font=font)
    label_addinfo.pack()

    label_etc = tk.Label(window, text="", font=font)
    label_etc.pack()
   
    label_comment = tk.Label(window_add, text="", font=font_comment)
    label_comment.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="nsew")

    # 추가로 grid된 라벨
    label_addcomment = tk.Label(window_add, text="", font=font_comment)
    label_addcomment.grid(row=1, column=0, padx=10, pady=(5, 0), sticky="nsew")
    

    # 중앙 정렬
    window_add.grid_rowconfigure(0, weight=1)
    window_add.grid_rowconfigure(1, weight=1)
    window_add.grid_columnconfigure(0, weight=1)
    
    label_info = tk.Label(window, text="시간대별 날씨 정보를 알고 싶다면, 스위치를 눌러주세요!",font=font_info)
    label_info.pack()

    tick1Min()
   
    # 버튼 감지 쓰레드 시작
    threading.Thread(target=detect_button_press, daemon=True).start()
   
    reset_timer()  # 타이머 초기화
   
    window.protocol("WM_DELETE_WINDOW", reset_face_detection)  # 창 닫기 시 처리
    window.mainloop()
    window_add.mainloop()

def reset_timer():
    global input_timer
    if input_timer:
        window.after_cancel(input_timer)  # 기존 타이머 취소
    input_timer = window.after(INACTIVITY_LIMIT, restart_program)  # 새로운 타이머 시작

def restart_program():
    os.execv(sys.executable, [sys.executable] + sys.argv)  # 현재 파이썬 프로그램을 다시 실행

if __name__ == '__main__':
    detect_faces_and_display_weather()
    GPIO.cleanup()

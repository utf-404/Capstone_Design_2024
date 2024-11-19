import firebase_admin
from firebase_admin import credentials, messaging

class FCMNotificationSender:
    def __init__(self, service_account_path):
        """
        FCMNotificationSender 초기화
        :param service_account_path: Firebase 서비스 계정 키 파일 경로
        """
        # Firebase Admin SDK 초기화
        self.cred = credentials.Certificate(service_account_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(self.cred)

    def send_topic_notification(self, topic, title, body):
        """
        특정 주제에 구독된 사용자들에게 푸시 알림을 전송하는 함수
        :param topic: 구독 주제 (예: "admin", "guardian")
        :param title: 알림 제목
        :param body: 알림 내용
        """
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic=topic,  # 주제에 대한 알림 전송
        )
        
        # FCM 서버에 알림 전송
        response = messaging.send(message)
        print(f'Successfully sent message to topic {topic}: {response}')

# 사용 예시
if __name__ == "__main__":
    # Firebase 서비스 계정 키 파일 경로
    service_account_path = './serviceAccountKey.json'

    # FCMNotificationSender 인스턴스 생성
    notification_sender = FCMNotificationSender(service_account_path)

    # 관리자(admin)에게 알림 전송
    #notification_sender.send_topic_notification("admin", "긴급: 요양환자 낙상", "요양환자가 낙상하였습니다. 즉시 조치가 필요합니다.")

    # 보호자(guardian)에게 알림 전송
    notification_sender.send_topic_notification("admin", "주의: Room 3 보호대상자 낙상", "보호대상자가 낙상하였습니다. 추가 정보는 요양시설로 문의하세요.")

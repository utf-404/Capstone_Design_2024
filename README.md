# 종합 설계 정리

# 🖥️ **요양시설 내 낙상 감지 모니터링 시스템**

**시니어를 위한 스마트 솔루션**

---

홍익대학교 2024학년도 제 21회 소프트웨어융합학과 학술제 팀 프로젝트

---

## **프로젝트 개발 필요성**

- 한국 사회는 급격한 고령화로 인해 70대 이상 인구가 처음으로 20대 인구를 앞지르는 변화를 겪고 있다. 이로 인해 생산 가능 인구와 초등학교 입학 예정 인구가 감소하고 있다. 고령 인구 증가로 요양 시설에서 일어나는 응급 상황에 대한 대비가 중요해지고 있다.

<img width="1131" alt="image" src="https://github.com/user-attachments/assets/8c207e81-c640-4d4d-83bc-72a9d13adee7">


- 이를 해결하기 위해 요양 시설 사고 대응 시스템 프로젝트가 추진되어, 응급 상황 시 신속하고 효과적으로 대응할 수 있는 시스템 구축을 목표로 하고 있다.
- 이와 관련하여 대한민국 보건복지부에서는 2023년 6월 22일부터 장기 요양시설에
- CCTV 설치를 의무화 할 것을 발표했다.
- 
<img width="712" alt="image 1" src="https://github.com/user-attachments/assets/07225b9c-fb36-4ea5-9c74-25516eca2b81">


---

## **연구 목적**

- 낙상 감지 알고리즘 개발
    - YOLOv8n-pose 기반 키포인트를 활용하여 낙상 여부와 자세 추적
- 병실 및 의류 색상 식별
    - RTSP 주소와 의류 색상 감지를 통해 낙상 위치 및 환자 상태 정보 추출
- 낙상 감지 및 통합 알림 시스템
    - 낙상 감지 알고리즘과 룸 및 색상 식별을 통해 모니터링 시스템과 알림 시스템 구축

---


## **낙상 감지 모니터링 시스템 구상도**

<img width="1094" alt="image 2" src="https://github.com/user-attachments/assets/1d10d0c8-7874-4238-b501-684b543c711f">


## 낙상 발생 시 알림 과정


<img width="1291" alt="image 3" src="https://github.com/user-attachments/assets/2d9dc0b6-442b-4a0a-9b10-3d271e7188bc">


## 낙상 감지 알고리즘 과정


<img width="1287" alt="image 4" src="https://github.com/user-attachments/assets/d00f257f-ddd3-4b9f-8418-282985f2aabb">


## 키 포인트 좌표 추출


<img width="1264" alt="image 5" src="https://github.com/user-attachments/assets/d93f0f4b-8204-454b-ae98-1b93ad044add">


<img width="1320" alt="image 6" src="https://github.com/user-attachments/assets/c90f9f9a-a551-4a89-9072-68c3a2d7f579">


## 상태정의


<img width="1251" alt="image 7" src="https://github.com/user-attachments/assets/198d50b6-033e-4fbc-96b6-7520d61d6ac4">


## 임계값 비교


<img width="1331" alt="image 8" src="https://github.com/user-attachments/assets/5112279d-4560-4452-bf23-c826069d288f">


## 낙상탐지


<img width="1270" alt="image 9" src="https://github.com/user-attachments/assets/5aa1cecd-5808-405a-aa7c-9ee1672ae177">


## RTSP 및 OpenCV를 활용한 통합 알림 시스템


<img width="1276" alt="image 10" src="https://github.com/user-attachments/assets/f646bc3e-ad4f-4cd9-b6b7-e7d29225838c">


## 결과물

관리자 웹 페이지 메인 화면


<img width="1441" alt="image 11" src="https://github.com/user-attachments/assets/7efaff92-a0b0-48a3-bc56-cb517191bd62">



관리자 메인 앱 


<img width="421" alt="image 12" src="https://github.com/user-attachments/assets/e64ae01c-c25a-46a0-af35-d8ca1f610af7">


보호자 메인 앱


<img width="402" alt="image 13" src="https://github.com/user-attachments/assets/2b67967f-a941-40c5-af73-4d4c4359d17e">


모니터링 시스템 화면 


<img width="1362" alt="image 14" src="https://github.com/user-attachments/assets/b91a897e-b309-4dc2-a592-6d9bbdb4dcb6">


낙상 감지 시 APP 알림 화면 및 화면 캡쳐


<img width="1335" alt="image 15" src="https://github.com/user-attachments/assets/3aa551ed-9a4b-4a58-92a4-d8dae5368b64">


## 정확도


<img width="1117" alt="image 16" src="https://github.com/user-attachments/assets/f876e0f3-cca7-448b-a42b-75458e9c5529">


## 대외활동


<img width="1412" alt="image 17" src="https://github.com/user-attachments/assets/044a7a67-15f7-4aea-9c2b-9710e155d891">


## 진행 상황


<img width="1368" alt="image 18" src="https://github.com/user-attachments/assets/d0e0cda8-b1eb-44a3-b6fd-e62ced266ff5">


## 기대 효과


<img width="1064" alt="image 19" src="https://github.com/user-attachments/assets/adc88969-c217-45b3-bb89-64b2622f7c2e">

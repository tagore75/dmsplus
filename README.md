# 바이탈사인 검출 시스템 (Vital Signs Detection System)

웹캠을 사용하여 비접촉 방식으로 심박수, 호흡수, 혈압을 측정하는 실시간 바이탈사인 검출 시스템입니다.

## 주요 기능

### 1. 심박수 검출 (Heart Rate Detection)
- **기술**: rPPG (remote Photoplethysmography)
- **방법**: 얼굴 이마 영역의 녹색 채널 분석
- **측정 범위**: 45-200 BPM
- **정상 범위**: 60-100 BPM

### 2. 호흡수 검출 (Respiratory Rate Detection)
- **기술**: MediaPipe Pose + 움직임 분석
- **방법**: 어깨/가슴 부위의 상하 움직임 추적
- **측정 범위**: 8-35 회/분
- **정상 범위**: 12-20 회/분

### 3. 혈압 추정 (Blood Pressure Estimation)
- **기술**: PPG 신호 분석 + 심박수 기반 추정
- **방법**: 맥파 특성 및 심박수 변화 분석
- **참고**: 추정값이므로 의료용으로 사용하지 마세요

## 시스템 구조

```
dmsplus/
├── app.py                      # Flask 백엔드 서버
├── requirements.txt            # Python 의존성
├── vital_signs/               # 바이탈사인 검출 모듈
│   ├── __init__.py
│   ├── heart_rate.py          # 심박수 검출
│   ├── respiratory_rate.py    # 호흡수 검출
│   └── blood_pressure.py      # 혈압 추정
└── frontend/                  # 웹 인터페이스
    ├── index.html
    ├── style.css
    └── script.js
```

## 설치 및 실행

### 1. 요구사항

- Python 3.8 이상
- 웹캠
- 최신 웹 브라우저 (Chrome, Firefox, Edge 등)

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd dmsplus

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 실행

```bash
# 서버 시작
python app.py
```

서버가 시작되면 브라우저에서 `http://localhost:5000`으로 접속하세요.

## 사용 방법

### 기본 측정

1. 웹 브라우저에서 애플리케이션을 엽니다
2. 카메라 접근을 허용합니다
3. **측정 시작** 버튼을 클릭합니다
4. 다음 사항을 준수하세요:
   - 조명이 밝은 곳에서 측정
   - 얼굴이 화면 중앙에 위치
   - 이마가 잘 보이도록 유지 (심박수)
   - 상체가 보이도록 유지 (호흡수)
   - 최소 10초 이상 측정

### 혈압 보정 (선택사항)

더 정확한 혈압 추정을 위해 실제 측정값으로 보정할 수 있습니다:

1. 혈압계로 실제 혈압을 측정합니다
2. 수축기/이완기 값을 입력 필드에 입력합니다
3. **보정** 버튼을 클릭합니다

## API 엔드포인트

### POST /api/process_frame
비디오 프레임을 처리하고 바이탈사인을 반환합니다.

**요청:**
```json
{
  "session_id": "unique_session_id",
  "frame": "base64_encoded_image",
  "timestamp": 1234567890.123
}
```

**응답:**
```json
{
  "session_id": "unique_session_id",
  "timestamp": 1234567890.123,
  "heart_rate": {
    "value": 72.5,
    "status": "success",
    "message": "Heart rate detected"
  },
  "respiratory_rate": {
    "value": 16.2,
    "status": "success",
    "message": "Respiratory rate detected"
  },
  "blood_pressure": {
    "systolic": 118.5,
    "diastolic": 78.3,
    "status": "success",
    "message": "Blood pressure estimated",
    "pulse_pressure": 40.2,
    "map": 91.7
  }
}
```

### POST /api/reset
세션을 초기화합니다.

### POST /api/calibrate_bp
혈압 추정 모델을 보정합니다.

### GET /api/health
서버 상태를 확인합니다.

## 기술적 세부사항

### 심박수 검출 알고리즘

1. Haar Cascade로 얼굴 감지
2. 이마 영역 추출 (ROI)
3. 녹색 채널 평균값 수집 (300 프레임)
4. 신호 전처리:
   - Detrending
   - Hamming window 적용
5. FFT로 주파수 분석
6. 0.8-3 Hz 대역 필터링 (48-180 BPM)
7. 피크 주파수를 BPM으로 변환

### 호흡수 검출 알고리즘

1. MediaPipe Pose로 어깨 랜드마크 감지
2. 가슴 중심점 계산
3. 수직 움직임 추적 (300 프레임)
4. 신호 전처리
5. FFT로 주파수 분석
6. 0.1-0.5 Hz 대역 필터링 (6-30 회/분)
7. 피크 주파수를 회/분으로 변환

### 혈압 추정 알고리즘

1. PPG 신호에서 맥파 특성 추출
2. 심박수와의 상관관계 분석
3. 맥파 폭과 진폭 분석
4. 경험적 모델로 수축기/이완기 추정
5. 보정값으로 정확도 개선

## 제한사항 및 주의사항

⚠️ **중요: 이 시스템은 교육 및 연구 목적으로만 사용하세요**

- **의료용 기기가 아닙니다**: 의료 진단이나 치료 결정에 사용하지 마세요
- **정확도 한계**: 실제 의료 기기보다 정확도가 낮을 수 있습니다
- **환경 의존성**: 조명, 움직임, 카메라 품질에 영향을 받습니다
- **혈압 추정**: 특히 혈압은 추정값이며 실제 측정값과 차이가 있을 수 있습니다

### 정확도를 높이는 방법

1. **좋은 조명**: 자연광 또는 밝은 조명 사용
2. **안정된 자세**: 움직이지 않고 편안한 자세 유지
3. **충분한 시간**: 최소 15-30초 측정
4. **카메라 품질**: 고해상도 웹캠 사용
5. **정기 보정**: 실제 측정값으로 혈압 보정

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

## 참고문헌

- rPPG: Verkruysse, W., et al. (2008). "Remote plethysmographic imaging using ambient light."
- MediaPipe: Google's MediaPipe Solutions
- PPG Signal Processing: Allen, J. (2007). "Photoplethysmography and its application in clinical physiological measurement."

## 문제 해결

### 카메라가 작동하지 않음
- 브라우저의 카메라 권한을 확인하세요
- HTTPS 연결을 사용하거나 localhost에서 테스트하세요

### 측정값이 나타나지 않음
- 얼굴이 화면에 잘 보이는지 확인하세요
- 조명이 충분한지 확인하세요
- 최소 10초 이상 측정하세요

### 측정값이 부정확함
- 환경 조명을 개선하세요
- 카메라와의 거리를 조정하세요
- 움직임을 최소화하세요
- 혈압 보정을 수행하세요

## 기여

이슈 리포트와 풀 리퀘스트를 환영합니다!

## 연락처

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해주세요.

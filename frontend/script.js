// Vital Signs Detection - Frontend JavaScript

class VitalSignsMonitor {
    constructor() {
        this.video = document.getElementById('webcam');
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.sessionId = this.generateSessionId();
        this.isRunning = false;
        this.stream = null;
        this.processingInterval = null;
        this.frameRate = 30; // Process at 30 FPS
        this.apiUrl = window.location.origin;

        this.initializeElements();
        this.initializeEventListeners();
        this.requestCameraAccess();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    initializeElements() {
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.calibrateBtn = document.getElementById('calibrateBtn');
        this.statusDiv = document.getElementById('status');

        // Vital sign displays
        this.heartRateDisplay = document.getElementById('heartRate');
        this.respiratoryRateDisplay = document.getElementById('respiratoryRate');
        this.systolicDisplay = document.getElementById('systolic');
        this.diastolicDisplay = document.getElementById('diastolic');

        // Status displays
        this.hrStatusDisplay = document.getElementById('hrStatus');
        this.rrStatusDisplay = document.getElementById('rrStatus');
        this.bpStatusDisplay = document.getElementById('bpStatus');
    }

    initializeEventListeners() {
        this.startBtn.addEventListener('click', () => this.startMonitoring());
        this.stopBtn.addEventListener('click', () => this.stopMonitoring());
        this.resetBtn.addEventListener('click', () => this.reset());
        this.calibrateBtn.addEventListener('click', () => this.calibrateBloodPressure());
    }

    async requestCameraAccess() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                }
            });

            this.video.srcObject = this.stream;

            this.video.onloadedmetadata = () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            };

            this.updateStatus('카메라 준비 완료. 측정을 시작하려면 버튼을 클릭하세요.', 'success');

        } catch (error) {
            console.error('Camera access error:', error);
            this.updateStatus('카메라 접근 실패: ' + error.message, 'error');
        }
    }

    startMonitoring() {
        if (!this.stream) {
            this.updateStatus('카메라가 준비되지 않았습니다.', 'error');
            return;
        }

        this.isRunning = true;
        this.startBtn.disabled = true;
        this.stopBtn.disabled = false;

        this.updateStatus('측정 중... 움직이지 말고 카메라를 바라보세요.', 'info');

        // Process frames at specified frame rate
        this.processingInterval = setInterval(() => {
            this.processFrame();
        }, 1000 / this.frameRate);

        // Add visual indicator
        document.querySelectorAll('.vital-card').forEach(card => {
            card.classList.add('measuring');
        });
    }

    stopMonitoring() {
        this.isRunning = false;
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;

        if (this.processingInterval) {
            clearInterval(this.processingInterval);
            this.processingInterval = null;
        }

        this.updateStatus('측정이 중지되었습니다.', 'info');

        // Remove visual indicator
        document.querySelectorAll('.vital-card').forEach(card => {
            card.classList.remove('measuring');
        });
    }

    async processFrame() {
        if (!this.isRunning) return;

        try {
            // Draw current frame to canvas
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

            // Convert canvas to base64
            const frameData = this.canvas.toDataURL('image/jpeg', 0.8);

            // Send to backend
            const response = await fetch(`${this.apiUrl}/api/process_frame`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    frame: frameData,
                    timestamp: Date.now() / 1000
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.updateDisplay(data);

        } catch (error) {
            console.error('Frame processing error:', error);
            if (this.isRunning) {
                this.updateStatus('처리 오류: ' + error.message, 'error');
            }
        }
    }

    updateDisplay(data) {
        // Update heart rate
        if (data.heart_rate && data.heart_rate.value !== null) {
            this.heartRateDisplay.textContent = data.heart_rate.value.toFixed(0);
            this.hrStatusDisplay.textContent = data.heart_rate.message;

            // Color code based on normal ranges (60-100 BPM)
            const hr = data.heart_rate.value;
            if (hr < 60 || hr > 100) {
                this.heartRateDisplay.style.color = '#ff9800';
            } else {
                this.heartRateDisplay.style.color = '#4caf50';
            }
        } else {
            this.heartRateDisplay.textContent = '--';
            this.hrStatusDisplay.textContent = data.heart_rate?.message || '측정 중';
        }

        // Update respiratory rate
        if (data.respiratory_rate && data.respiratory_rate.value !== null) {
            this.respiratoryRateDisplay.textContent = data.respiratory_rate.value.toFixed(0);
            this.rrStatusDisplay.textContent = data.respiratory_rate.message;

            // Color code based on normal ranges (12-20 BPM)
            const rr = data.respiratory_rate.value;
            if (rr < 12 || rr > 20) {
                this.respiratoryRateDisplay.style.color = '#ff9800';
            } else {
                this.respiratoryRateDisplay.style.color = '#4caf50';
            }
        } else {
            this.respiratoryRateDisplay.textContent = '--';
            this.rrStatusDisplay.textContent = data.respiratory_rate?.message || '측정 중';
        }

        // Update blood pressure
        if (data.blood_pressure && data.blood_pressure.systolic !== null) {
            this.systolicDisplay.textContent = data.blood_pressure.systolic.toFixed(0);
            this.diastolicDisplay.textContent = data.blood_pressure.diastolic.toFixed(0);
            this.bpStatusDisplay.textContent = data.blood_pressure.message;

            // Color code based on normal ranges
            const sys = data.blood_pressure.systolic;
            const dia = data.blood_pressure.diastolic;

            if (sys > 140 || dia > 90) {
                this.systolicDisplay.style.color = '#f44336';
                this.diastolicDisplay.style.color = '#f44336';
            } else if (sys < 90 || dia < 60) {
                this.systolicDisplay.style.color = '#ff9800';
                this.diastolicDisplay.style.color = '#ff9800';
            } else {
                this.systolicDisplay.style.color = '#4caf50';
                this.diastolicDisplay.style.color = '#4caf50';
            }
        } else {
            this.systolicDisplay.textContent = '--';
            this.diastolicDisplay.textContent = '--';
            this.bpStatusDisplay.textContent = data.blood_pressure?.message || '측정 중';
        }
    }

    async reset() {
        // Stop monitoring if running
        if (this.isRunning) {
            this.stopMonitoring();
        }

        // Clear displays
        this.heartRateDisplay.textContent = '--';
        this.respiratoryRateDisplay.textContent = '--';
        this.systolicDisplay.textContent = '--';
        this.diastolicDisplay.textContent = '--';

        this.hrStatusDisplay.textContent = '대기 중';
        this.rrStatusDisplay.textContent = '대기 중';
        this.bpStatusDisplay.textContent = '대기 중';

        // Reset colors
        this.heartRateDisplay.style.color = '#1a1a1a';
        this.respiratoryRateDisplay.style.color = '#1a1a1a';
        this.systolicDisplay.style.color = '#1a1a1a';
        this.diastolicDisplay.style.color = '#1a1a1a';

        // Reset backend session
        try {
            await fetch(`${this.apiUrl}/api/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            this.updateStatus('초기화 완료', 'success');
        } catch (error) {
            console.error('Reset error:', error);
            this.updateStatus('초기화 오류: ' + error.message, 'error');
        }

        // Generate new session ID
        this.sessionId = this.generateSessionId();
    }

    async calibrateBloodPressure() {
        const systolic = parseFloat(document.getElementById('calibSystolic').value);
        const diastolic = parseFloat(document.getElementById('calibDiastolic').value);

        if (!systolic || !diastolic) {
            alert('수축기와 이완기 혈압을 모두 입력하세요.');
            return;
        }

        if (systolic <= diastolic) {
            alert('수축기 혈압은 이완기 혈압보다 커야 합니다.');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/calibrate_bp`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    systolic: systolic,
                    diastolic: diastolic,
                    heart_rate: parseFloat(this.heartRateDisplay.textContent) || 70
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateStatus('혈압 보정 완료', 'success');
                document.getElementById('calibSystolic').value = '';
                document.getElementById('calibDiastolic').value = '';
            } else {
                throw new Error(data.message || '보정 실패');
            }

        } catch (error) {
            console.error('Calibration error:', error);
            this.updateStatus('보정 오류: ' + error.message, 'error');
        }
    }

    updateStatus(message, type = 'info') {
        this.statusDiv.textContent = message;
        this.statusDiv.className = 'status-message';

        if (type === 'success') {
            this.statusDiv.classList.add('success');
        } else if (type === 'error' || type === 'warning') {
            this.statusDiv.classList.add('warning');
        }
    }

    cleanup() {
        this.stopMonitoring();

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const monitor = new VitalSignsMonitor();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        monitor.cleanup();
    });
});

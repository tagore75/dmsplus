"""
Vital Signs Detection API Server
Flask application providing endpoints for vital signs monitoring
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np
import base64
import time
from vital_signs import HeartRateDetector, RespiratoryRateDetector, BloodPressureEstimator

app = Flask(__name__, static_folder='frontend')
CORS(app)

# Global detector instances (in production, use session-based storage)
detectors = {}


def get_or_create_detector(session_id):
    """Get or create detector instances for a session"""
    if session_id not in detectors:
        detectors[session_id] = {
            'heart_rate': HeartRateDetector(buffer_size=300, fps=30),
            'respiratory': RespiratoryRateDetector(buffer_size=300, fps=30),
            'blood_pressure': BloodPressureEstimator(buffer_size=300),
            'created_at': time.time()
        }
    return detectors[session_id]


def cleanup_old_sessions(max_age=3600):
    """Remove sessions older than max_age seconds"""
    current_time = time.time()
    to_remove = []
    for session_id, detector_set in detectors.items():
        if current_time - detector_set['created_at'] > max_age:
            to_remove.append(session_id)

    for session_id in to_remove:
        del detectors[session_id]


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('frontend', 'index.html')


@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    """
    Process a video frame and return vital signs

    Expected JSON payload:
    {
        "session_id": "unique_session_identifier",
        "frame": "base64_encoded_image",
        "timestamp": timestamp_in_seconds
    }
    """
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        frame_data = data.get('frame')
        timestamp = data.get('timestamp', time.time())

        if not frame_data:
            return jsonify({'error': 'No frame data provided'}), 400

        # Decode base64 image
        img_data = base64.b64decode(frame_data.split(',')[1] if ',' in frame_data else frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': 'Invalid image data'}), 400

        # Get detector instances
        detector_set = get_or_create_detector(session_id)
        hr_detector = detector_set['heart_rate']
        resp_detector = detector_set['respiratory']
        bp_estimator = detector_set['blood_pressure']

        # Process heart rate
        hr_result = hr_detector.process_frame(frame, timestamp)

        # Process respiratory rate
        resp_result = resp_detector.process_frame(frame, timestamp)

        # Update blood pressure estimator with PPG signal
        if hr_result['success']:
            # Add green channel values from heart rate detector
            if len(hr_detector.green_values) > 0:
                bp_estimator.add_ppg_sample(hr_detector.green_values[-1])
            bp_estimator.add_heart_rate(hr_result['heart_rate'])

        # Estimate blood pressure
        bp_result = bp_estimator.estimate_blood_pressure(hr_result.get('heart_rate'))

        # Compile results
        response = {
            'session_id': session_id,
            'timestamp': timestamp,
            'heart_rate': {
                'value': hr_result.get('heart_rate'),
                'status': 'success' if hr_result['success'] else 'collecting',
                'message': hr_result.get('message', '')
            },
            'respiratory_rate': {
                'value': resp_result.get('respiratory_rate'),
                'status': 'success' if resp_result['success'] else 'collecting',
                'message': resp_result.get('message', '')
            },
            'blood_pressure': {
                'systolic': bp_result.get('systolic'),
                'diastolic': bp_result.get('diastolic'),
                'status': 'success' if bp_result['success'] else 'collecting',
                'message': bp_result.get('message', ''),
                'pulse_pressure': bp_result.get('pulse_pressure'),
                'map': bp_result.get('mean_arterial_pressure')
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset a session's detectors"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')

        if session_id in detectors:
            detector_set = detectors[session_id]
            detector_set['heart_rate'].reset()
            detector_set['respiratory'].reset()
            detector_set['blood_pressure'].reset()

        return jsonify({'success': True, 'message': 'Session reset'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calibrate_bp', methods=['POST'])
def calibrate_blood_pressure():
    """
    Calibrate blood pressure estimator with actual reading

    Expected JSON payload:
    {
        "session_id": "unique_session_identifier",
        "systolic": measured_systolic_value,
        "diastolic": measured_diastolic_value,
        "heart_rate": current_heart_rate
    }
    """
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        systolic = data.get('systolic')
        diastolic = data.get('diastolic')
        heart_rate = data.get('heart_rate', 70)

        if not systolic or not diastolic:
            return jsonify({'error': 'Systolic and diastolic values required'}), 400

        detector_set = get_or_create_detector(session_id)
        bp_estimator = detector_set['blood_pressure']

        result = bp_estimator.calibrate(systolic, diastolic, heart_rate)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'active_sessions': len(detectors),
        'timestamp': time.time()
    })


@app.before_request
def before_request():
    """Cleanup old sessions before each request"""
    cleanup_old_sessions()


if __name__ == '__main__':
    print("Starting Vital Signs Detection Server...")
    print("Server running on http://localhost:5000")
    print("\nEndpoints:")
    print("  GET  /                      - Web interface")
    print("  POST /api/process_frame     - Process video frame")
    print("  POST /api/reset             - Reset session")
    print("  POST /api/calibrate_bp      - Calibrate blood pressure")
    print("  GET  /api/health            - Health check")

    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import mediapipe as mp
import base64
from fito import calculate_angle, draw_concentration_bar, draw_concentration_bar_squat, draw_concentration_bar_biceps

app = Flask(__name__)
CORS(app)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Helper to decode base64 image

def decode_image(image_b64):
    img_bytes = base64.b64decode(image_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

# State for counting reps per session (very basic, resets on backend restart)
rep_state = {"squat": {"count": 0, "position": "up", "shoulder_initial_y": None},
             "pushup": {"count": 0, "position": None},
             "bicep_curl": {"count": 0, "position": "down"}}

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    image_b64 = data['image']
    exercise = data['exercise']
    img = decode_image(image_b64)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)
    feedback = ""
    count = rep_state[exercise]["count"] if exercise in rep_state else 0
    try:
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            if exercise == "squat":
                hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, 
                       landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, 
                        landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 
                         landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 
                            landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                angle = calculate_angle(hip, knee, ankle)
                # Rep logic
                if rep_state["squat"]["position"] == "up" and rep_state["squat"]["shoulder_initial_y"] is None:
                    rep_state["squat"]["shoulder_initial_y"] = shoulder[1]
                if angle > 160:
                    rep_state["squat"]["position"] = "up"
                    rep_state["squat"]["shoulder_initial_y"] = shoulder[1]
                if angle < 90 and rep_state["squat"]["position"] == "up" and shoulder[1] > rep_state["squat"]["shoulder_initial_y"] + 0.02:
                    rep_state["squat"]["position"] = "down"
                    rep_state["squat"]["count"] += 1
                count = rep_state["squat"]["count"]
                if angle > 160:
                    feedback = "Stand tall!"
                elif angle < 90:
                    feedback = "Squat low!"
                else:
                    feedback = "Good depth!"
            elif exercise == "pushup":
                shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                angle = calculate_angle(shoulder, elbow, wrist)
                if angle > 160:
                    rep_state["pushup"]["position"] = "up"
                if angle < 90 and rep_state["pushup"]["position"] == "up":
                    rep_state["pushup"]["position"] = "down"
                    rep_state["pushup"]["count"] += 1
                count = rep_state["pushup"]["count"]
                if 80 < angle < 160:
                    feedback = "Good form!"
                else:
                    feedback = "Keep your core tight!"
            elif exercise == "bicep_curl":
                r_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, 
                              landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                r_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, 
                           landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                r_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, 
                           landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                l_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                              landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                l_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                           landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                l_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                           landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                r_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)
                l_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)
                # Rep logic
                if r_angle > 140 and l_angle > 140:
                    rep_state["bicep_curl"]["position"] = "down"
                if r_angle < 50 and l_angle < 50 and rep_state["bicep_curl"]["position"] == "down":
                    rep_state["bicep_curl"]["position"] = "up"
                    rep_state["bicep_curl"]["count"] += 1
                count = rep_state["bicep_curl"]["count"]
                if r_angle > 140 and l_angle > 140:
                    feedback = "Extend your arm!"
                elif r_angle < 50:
                    feedback = "Full curl!"
                else:
                    feedback = "Good form!"
            else:
                feedback = "Unknown exercise"
        else:
            feedback = "No pose detected"
    except Exception as e:
        feedback = f"Error: {str(e)}"
    return jsonify({"reps": count, "feedback": feedback})

@app.route('/')
def index():
    return "ProtoFit backend running."

if __name__ == '__main__':
    app.run(debug=True, port=5000)

const canvas = document.getElementById('overlay');
document.addEventListener('DOMContentLoaded', function() {
    const landingStartBtn = document.getElementById('landing-start-btn');
    const landingSection = document.getElementById('landing');
    const trackingSection = document.getElementById('tracking-section');
    if (landingStartBtn && trackingSection && landingSection) {
        landingStartBtn.addEventListener('click', function() {
            trackingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            setTimeout(() => {
                landingSection.style.display = 'none';
            }, 900);
        });
    }
});
const ctx = canvas.getContext('2d');
const startBtn = document.getElementById('start-btn');
const exerciseSelect = document.getElementById('exercise-select');
const repCountSpan = document.getElementById('rep-count');
const feedbackMsg = document.getElementById('feedback-msg');

let streaming = false;
let intervalId = null;
let videoStream = null;
let video = null; // Offscreen video element

function startWebcam() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video = document.createElement('video');
            video.style.display = 'none';
            document.body.appendChild(video);
            video.srcObject = stream;
            video.play();
            streaming = true;
            videoStream = stream;
            video.onloadedmetadata = () => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                requestAnimationFrame(drawVideoToCanvas);
            };
        })
        .catch(err => {
            alert('Could not access webcam: ' + err);
        });
}

function drawVideoToCanvas() {
    if (video && video.readyState === 4) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }
    if (streaming) {
        requestAnimationFrame(drawVideoToCanvas);
    }
}

function sendFrameToBackend() {
    if (!video || video.readyState !== 4) return;
    // Only send frame, don't update display here
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    tempCanvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = tempCanvas.toDataURL('image/jpeg');
    const base64 = dataUrl.split(',')[1];
    fetch('http://localhost:5000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            image: base64,
            exercise: exerciseSelect.value
        })
    })
    .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    })
    .then(data => {
        repCountSpan.textContent = `Reps: ${data.reps}`;
        feedbackMsg.textContent = data.feedback;
    })
    .catch((err) => {
        feedbackMsg.textContent = 'Error connecting to backend.';
    });
}

startBtn.onclick = () => {
    if (!streaming) {
        startWebcam();
    }
    if (!intervalId) {
        // Show video at full frame rate, send to backend at 200ms (5 fps)
        intervalId = setInterval(sendFrameToBackend, 200);
        startBtn.disabled = true;
        feedbackMsg.textContent = 'Tracking...';
    }
};

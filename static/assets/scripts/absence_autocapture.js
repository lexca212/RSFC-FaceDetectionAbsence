// --- CONFIG ---
const BLINK_EAR_THRESHOLD = 0.18;    // EAR < threshold dianggap mata tertutup
const BLINK_FRAMES_MIN = 2;          // minimal frame EAR < threshold untuk valid blink
const CAPTURE_COOLDOWN_MS = 3000;    // setelah capture, tunggu dulu (avoid duplicate)
const DRAW_LANDMARKS = true;         // tampilkan overlay titik (debug)

const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const overlayCtx = overlay.getContext('2d');
const photoInput = document.getElementById('photoInput');
const manualCaptureBtn = document.getElementById('manualCaptureBtn');

let blinkFrames = 0;
let blinkDetected = false;
let lastCaptureAt = 0;

function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

function EAR(eye) {
  // eye points order expected: [p1, p2, p3, p4, p5, p6]
  const vertical1 = distance(eye[1], eye[5]);
  const vertical2 = distance(eye[2], eye[4]);
  const horizontal = distance(eye[0], eye[3]);
  return (vertical1 + vertical2) / (2.0 * horizontal);
}

const LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380];

function resizeOverlay() {
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
}

function drawLandmarks(landmarks) {
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  overlayCtx.lineWidth = 1;
  overlayCtx.strokeStyle = 'rgba(0,255,0,0.8)';
  overlayCtx.fillStyle = 'rgba(255,0,0,0.8)';
  for (let i = 0; i < landmarks.length; i++) {
    const x = landmarks[i].x * overlay.width;
    const y = landmarks[i].y * overlay.height;
    overlayCtx.beginPath();
    overlayCtx.arc(x, y, 1.2, 0, Math.PI * 2);
    overlayCtx.fill();
  }
}

function autoCaptureAndSend() {
  const now = Date.now();
  if (now - lastCaptureAt < CAPTURE_COOLDOWN_MS) return;
  lastCaptureAt = now;

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const imageData = canvas.toDataURL('image/jpeg', 0.85);
  photoInput.value = imageData;

  toastr.success('Gambar wajah berhasil diambil (kedipan terdeteksi).');

  const form = document.getElementById('absenForm');
  const fd = new FormData(form);

  $.ajax({
    url: ABSENCE_URL,
    method: 'POST',
    data: fd,
    processData: false,
    contentType: false,
    success: function(response) {
      if (response.status === 'success') {
        let content = `
          <div class="mt-3">
            <p class="mb-1">
              <strong style="color: ${
                (response.status_absen === 'Terlambat' || response.status_absen === 'Pulang Cepat') ? 'red' :
                (response.status_absen === 'Tepat Waktu' ? 'blue' : 'black')
              };">${response.status_absen}</strong>
            </p>
            <p class="mb-1"><strong>${response.time}</strong></p>
            <table style="text-align: left;">
              <tbody>
                <tr><td style="width:30%"><strong>NIK</strong></td><td>: ${response.nik}</td></tr>
                <tr><td><strong>Nama</strong></td><td>: ${response.name}</td></tr>
                <tr><td><strong>Tanggal</strong></td><td>: ${response.date}</td></tr>
              </tbody>
            </table>
            <p class="mb-1"><strong>${response.minor_message}</strong></p>
          </div>
        `;
        mpCamera.stop();
        Swal.fire({
          imageUrl: 'https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjY1NGVnaGg4bzNiemdmNGRyYXo1cWE1dWZxaG5heGR5bWJtOTg3ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/esVaNp1XK3h5vVwa1x/giphy.gif',
          imageWidth: 150,
          imageHeight: 150,
          title: response.message,
          html: content,
          showConfirmButton: true,
          confirmButtonText: 'OK',
          timer: 10000,
          timerProgressBar: true
        }).then((result) => {
          location.reload();
        });
      } else {
        toastr.error(response.message);
      }
    },
    error: function(xhr, status, err) {
      console.error('AJAX error', status, err);
      toastr.error('Terjadi kesalahan saat mengirim data.');
    }
  });
}

manualCaptureBtn.addEventListener('click', function(){
  autoCaptureAndSend();
});

const faceMesh = new FaceMesh({
  locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
  }
});

faceMesh.setOptions({
  maxNumFaces: 1,
  refineLandmarks: true,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.6
});

faceMesh.onResults((results) => {

    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
        overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
        blinkFrames = 0;
        blinkDetected = false;
        return;
    }

    const videoRect = video.getBoundingClientRect();
    overlay.width = videoRect.width;
    overlay.height = videoRect.height;

    const landmarks = results.multiFaceLandmarks[0];

    if (DRAW_LANDMARKS) {
        overlayCtx.clearRect(0, 0, overlay.width, overlay.height);

        for (let i = 0; i < landmarks.length; i++) {

            const x = landmarks[i].x * overlay.width;
            const y = landmarks[i].y * overlay.height;

            overlayCtx.beginPath();
            overlayCtx.arc(x, y, 2, 0, Math.PI * 2);
            overlayCtx.fillStyle = "red";
            overlayCtx.fill();
        }
    }

    const leftEye = LEFT_EYE_IDX.map(i => ({x: landmarks[i].x, y: landmarks[i].y}));
    const rightEye = RIGHT_EYE_IDX.map(i => ({x: landmarks[i].x, y: landmarks[i].y}));

    const earLeft = EAR(leftEye);
    const earRight = EAR(rightEye);
    const ear = (earLeft + earRight) / 2.0;

    if (ear < BLINK_EAR_THRESHOLD) {
        blinkFrames++;
    } else {
        if (blinkFrames >= BLINK_FRAMES_MIN && !blinkDetected) {
            blinkDetected = true;
            setTimeout(() => autoCaptureAndSend(), 150);
        }
        blinkFrames = 0;
    }

    if (blinkDetected && (Date.now() - lastCaptureAt) > CAPTURE_COOLDOWN_MS) {
        blinkDetected = false;
    }
});


const mpCamera = new Camera(video, {
  onFrame: async () => {
    await faceMesh.send({image: video});
  },
  width: 640,
  height: 480
});
// mpCamera.start();

let cameraStarted = false;

function startCameraAndFaceMesh() {
    if (cameraStarted) return;
    cameraStarted = true;

    video.addEventListener('loadedmetadata', () => {
        overlay.width = video.videoWidth;
        overlay.height = video.videoHeight;
    });

    mpCamera.start();
}

document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("introModal");
    const startButton = document.getElementById("startBtn");

    startButton.addEventListener("click", function() {
        modal.style.display = "none";
        startCameraAndFaceMesh();
    });
});

function updateDateTime() {
  const now = new Date();
  const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const formattedDate = now.toLocaleDateString('id-ID', dateOptions);
  let hours   = now.getHours().toString().padStart(2, '0');
  let minutes = now.getMinutes().toString().padStart(2, '0');
  let seconds = now.getSeconds().toString().padStart(2, '0');
  const formattedTime = `${hours}:${minutes}:${seconds}`;
  document.getElementById("dateDisplay").textContent = formattedDate;
  document.getElementById("timeDisplay").textContent = formattedTime;
}
setInterval(updateDateTime, 1000);
updateDateTime();
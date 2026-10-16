const video = document.querySelector('#registration-video');
const canvas = document.querySelector('#registration-canvas');
const preview = document.querySelector('#registration-preview');
const imageInput = document.querySelector('#registration-camera-image');
const startButton = document.querySelector('#registration-start-camera');
const captureButton = document.querySelector('#registration-capture');
const retakeButton = document.querySelector('#registration-retake');
const help = document.querySelector('#registration-camera-help');

let stream;

function stopCamera() {
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
}

startButton.addEventListener('click', async () => {
  help.hidden = true;
  if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) {
    help.textContent = 'A webcam exige uma conexão HTTPS ou localhost. Você ainda pode selecionar uma foto do dispositivo.';
    help.hidden = false;
    return;
  }

  startButton.disabled = true;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
    await video.play();
    video.hidden = false;
    captureButton.hidden = false;
    captureButton.disabled = false;
    startButton.hidden = true;
  } catch {
    stopCamera();
    startButton.disabled = false;
    help.textContent = 'Não foi possível acessar a webcam. Verifique a permissão do navegador ou selecione uma foto.';
    help.hidden = false;
  }
});

captureButton.addEventListener('click', () => {
  if (!video.videoWidth || !video.videoHeight) return;
  const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
  canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  imageInput.value = canvas.toDataURL('image/jpeg', 0.82);
  preview.src = imageInput.value;
  preview.hidden = false;
  video.hidden = true;
  captureButton.hidden = true;
  retakeButton.hidden = false;
  stopCamera();
});

retakeButton.addEventListener('click', () => {
  imageInput.value = '';
  preview.removeAttribute('src');
  preview.hidden = true;
  retakeButton.hidden = true;
  startButton.hidden = false;
  startButton.disabled = false;
});

window.addEventListener('pagehide', stopCamera);

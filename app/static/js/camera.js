const video = document.querySelector('#video');
const canvas = document.querySelector('#canvas');
const preview = document.querySelector('#preview');
const dataInput = document.querySelector('#image-data');
const capture = document.querySelector('#capture');
const retake = document.querySelector('#retake');
const submit = document.querySelector('#submit');
const cameraHelp = document.querySelector('#camera-help');
const photoFile = document.querySelector('#photo-file');

let cameraStream;

function stopCamera() {
  cameraStream?.getTracks().forEach(track => track.stop());
  cameraStream = null;
}

function setImage(dataUrl) {
  dataInput.value = dataUrl;
  preview.src = dataUrl;
  preview.style.display = 'block';
  video.style.display = 'none';
  capture.hidden = true;
  retake.hidden = false;
  submit.disabled = false;
  cameraHelp.hidden = true;
  stopCamera();
}

function imageToJpegDataUrl(image) {
  const sourceWidth = image.videoWidth || image.naturalWidth;
  const sourceHeight = image.videoHeight || image.naturalHeight;
  if (!sourceWidth || !sourceHeight) throw new Error('A imagem não tem dimensões válidas.');

  // Reduz fotos de alta resolução antes de transformá-las em texto Base64 no formulário.
  const scale = Math.min(1, 1600 / Math.max(sourceWidth, sourceHeight));
  canvas.width = Math.max(1, Math.round(sourceWidth * scale));
  canvas.height = Math.max(1, Math.round(sourceHeight * scale));
  const context = canvas.getContext('2d');
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.82);
}

async function startCamera() {
  capture.disabled = true;
  const localHost = ['localhost', '127.0.0.1', '::1'].includes(location.hostname);
  if ((!window.isSecureContext && !localHost) || !navigator.mediaDevices?.getUserMedia) {
    video.style.display = 'none';
    capture.hidden = true;
    cameraHelp.hidden = false;
    return;
  }

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = cameraStream;
    video.addEventListener('loadedmetadata', () => { capture.disabled = false; }, { once: true });
    video.style.display = 'block';
    capture.hidden = false;
    cameraHelp.hidden = true;
  } catch {
    video.style.display = 'none';
    capture.hidden = true;
    cameraHelp.hidden = false;
  }
}

startCamera();

capture.addEventListener('click', () => {
  if (!video.videoWidth || !video.videoHeight) return;
  setImage(imageToJpegDataUrl(video));
});

photoFile.addEventListener('change', () => {
  const file = photoFile.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    cameraHelp.textContent = 'Escolha um arquivo de imagem válido.';
    cameraHelp.hidden = false;
    return;
  }
  const objectUrl = URL.createObjectURL(file);
  const image = new Image();
  image.addEventListener('load', () => {
    try {
      setImage(imageToJpegDataUrl(image));
    } catch {
      cameraHelp.textContent = 'Não foi possível preparar essa foto. Tente outra imagem JPEG ou PNG.';
      cameraHelp.hidden = false;
      URL.revokeObjectURL(objectUrl);
    }
  }, { once: true });
  image.addEventListener('error', () => {
    cameraHelp.textContent = 'Não foi possível abrir essa foto. Tente outra imagem JPEG ou PNG.';
    cameraHelp.hidden = false;
    URL.revokeObjectURL(objectUrl);
  }, { once: true });
  image.src = objectUrl;
});

retake.addEventListener('click', () => {
  dataInput.value = '';
  photoFile.value = '';
  preview.removeAttribute('src');
  preview.style.display = 'none';
  submit.disabled = true;
  retake.hidden = true;
  startCamera();
});

window.addEventListener('pagehide', stopCamera);

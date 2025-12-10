$(function () {
  // Toastr configuration
  toastr.options = {
    "closeButton": true,
    "debug": false,
    "newestOnTop": false,
    "progressBar": true,
    "positionClass": "toast-top-right",
    "preventDuplicates": false,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
  }

  // Inisialisasi Kamera
  const cameraFeed = document.getElementById('camera-feed');
  const photoCanvas = document.getElementById('photo-canvas');
  const photoPreview = document.getElementById('photo-preview');
  const captureButton = document.getElementById('capture-photo');
  const photoDataInput = document.getElementById('photo-data');

  async function initCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      cameraFeed.srcObject = stream;
    } catch (error) {
      console.error('Error accessing camera:', error);
      toastr.error('Tidak dapat mengakses kamera. Pastikan kamera terhubung dan izin diberikan.');
    }
  }

  initCamera();

  captureButton.addEventListener('click', function () {
    photoCanvas.width = cameraFeed.videoWidth;
    photoCanvas.height = cameraFeed.videoHeight;
    photoCanvas.getContext('2d').drawImage(cameraFeed, 0, 0);
    const photoData = photoCanvas.toDataURL('image/jpeg');
    photoPreview.src = photoData;
    photoPreview.style.display = 'block';
    photoDataInput.value = photoData;
  });

  // Form submission
  $('form').on('submit', function (e) {
    e.preventDefault();
    var formData = new FormData(this);

    $.ajax({
      url: $(this).attr('action'),
      type: 'POST',
      data: formData,
      success: function (response) {
        if (response.status === 'success'){
          toastr.success(response.message);
        } else {
          toastr.error(response.message);
        }
        console.log(response)
        $('form')[0].reset();
        photoPreview.style.display = 'none';
      },
      error: function (xhr, status, error) {
        toastr.error('Terjadi kesalahan saat mengupload data.');
      },
      cache: false,
      contentType: false,
      processData: false
    });
  });

  // Add ripple effect to buttons
  $('.button').on('click', function (e) {
    let x = e.clientX - e.target.offsetLeft;
    let y = e.clientY - e.target.offsetTop;
    let ripple = document.createElement('span');
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    this.appendChild(ripple);
    setTimeout(() => {
      ripple.remove();
    }, 600);
  });
});
function startCamera() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            const video = document.querySelector('video');
            video.srcObject = stream;
        });
}

function updateDateTime() {
    const now = new Date();

    const dateOptions = {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };
    const formattedDate = now.toLocaleDateString('id-ID', dateOptions);

    const timeOptions = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    var formattedTime = now.toLocaleTimeString('id-ID', timeOptions);

    let hours   = now.getHours().toString().padStart(2, '0');
    let minutes = now.getMinutes().toString().padStart(2, '0');
    let seconds = now.getSeconds().toString().padStart(2, '0');

    formattedTime = `${hours}:${minutes}:${seconds}`;

    document.getElementById("dateDisplay").textContent = formattedDate;
    document.getElementById("timeDisplay").textContent = formattedTime;
}

setInterval(updateDateTime, 1000);
updateDateTime();

function capturePhoto() {
    const video = document.querySelector('video');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas ke base64 string
    const photo = canvas.toDataURL('image/jpeg');
    document.getElementById('photoInput').value = photo;

    toastr.success('Berhasil mengambil foto!');
}

$(document).ready(function() {
    $('#absenForm').on('submit', function(e) {
        e.preventDefault();

        var formData = new FormData(this);
        console.log(formData);

        $.ajax({
            url: ABSENCE_URL,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.status === 'success') {
                    toastr.success(response.message);
                    $('#nikResult').text('NIK: ' + response.nik);
                    $('#nameResult').text('Nama: ' + response.name);
                    $('#dateResult').text('Waktu Absensi: ' + response.date);
                    $('#resultDisplay').fadeIn(500);
                    setTimeout(function() {
                        location.reload();
                    }, 5000);
                } else {
                    toastr.error(response.message);
                }
            },
            error: function() {
                console.error('AJAX error:', textStatus, errorThrown, jqXHR.responseText);
                toastr.error('Terjadi kesalahan saat mengirim data.');
            }
        });
    });
});

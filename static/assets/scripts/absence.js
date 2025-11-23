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
                    // toastr.success(response.message);
                    // $('#nikResult').text('NIK: ' + response.nik);
                    // $('#nameResult').text('Nama: ' + response.name);
                    // $('#dateResult').text('Waktu Absensi: ' + response.date);
                    // $('#resultDisplay').fadeIn(500);
                    // setTimeout(function() {
                    //     location.reload();
                    // }, 5000);
                    let content = `
                        <div class="mt-3">
                            <p class="mb-1">
                                <strong style="color: 
                                    ${(response.status_absen === 'Terlambat' || response.status_absen === 'Pulang Cepat') ? 'red' : 
                                    (response.status_absen === 'Tepat Waktu' ? 'blue' : 'black')};"
                                >
                                ${response.status_absen}
                                </strong>
                            </p>
                            <p class="mb-1"><strong>${response.time}</strong></p>
                            <table style="text-align: left;">
                                <tbody>
                                    <tr>
                                        <td style="width: 30%;"><strong>NIK</strong></td>
                                        <td>: ${response.nik}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Nama</strong></td>
                                        <td>: ${response.name}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Tanggal</strong></td>
                                        <td>: ${response.date}</td>
                                    </tr>
                                </tbody>
                            </table>
                            <p class="mb-1"><strong>${response.minor_message}</strong></p>
                        </div>
                    `;

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
            error: function() {
                console.error('AJAX error:', textStatus, errorThrown, jqXHR.responseText);
                toastr.error('Terjadi kesalahan saat mengirim data.');
            }
        });
    });
});

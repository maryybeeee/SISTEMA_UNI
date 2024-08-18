document.addEventListener('DOMContentLoaded', function() {
    const userIcon = document.getElementById('user-icon');
    const sideMenu = document.getElementById('side-menu');
    const closeBtn = document.getElementById('close-btn');

    // Función para abrir el menú lateral
    function openSideMenu() {
        sideMenu.style.width = '350px';
    }

    // Función para cerrar el menú lateral
    function closeSideMenu() {
        sideMenu.style.width = '0';
    }

    // Evento de clic en el icono de usuario para abrir el menú lateral
    userIcon.addEventListener('click', function(event) {
        event.stopPropagation();
        openSideMenu();
    });

    // Evento de clic en el botón de cerrar para cerrar el menú lateral
    closeBtn.addEventListener('click', function(event) {
        event.stopPropagation();
        closeSideMenu();
    });

    // Cerrar el menú lateral al hacer clic fuera de él
    window.addEventListener('click', function(event) {
        if (event.target !== sideMenu && !sideMenu.contains(event.target) && event.target !== userIcon) {
            closeSideMenu();
        }
    });

    sideMenu.addEventListener('click', function(event) {
        event.stopPropagation();
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const fileInputs = document.querySelectorAll('.file-input');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files.length > 0 ? this.files[0].name : 'No se ha seleccionado archivo';
            const fileNameSpan = document.getElementById(`file-name-${this.id.split('-').slice(2).join('-')}`);
            fileNameSpan.textContent = fileName;
        });
    });
});

document.addEventListener("DOMContentLoaded", function() {
    setTimeout(function() {
        var flashes = document.querySelectorAll('.flashes li');
        flashes.forEach(function(flash) {
            flash.style.display = 'none';
        });
    }, 5000);
});

function togglePasswordVisibility(passwordFieldId, iconElement) {
    var passwordField = document.getElementById(passwordFieldId);
    var icon = iconElement.querySelector('i');
    
    if (passwordField.type === "password") {
        passwordField.type = "text";
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        passwordField.type = "password";
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

function deleteValue(column) {
    const form = document.createElement('form');
    form.method = 'post';
    form.action = `{{ url_for('edit_record', record_id=record['NoControl']) }}`;
    
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'column_name';
    input.value = column;
    form.appendChild(input);
    
    document.body.appendChild(form);
    form.submit();
}

document.addEventListener('DOMContentLoaded', function() {
    var loadingScreen = document.getElementById('loading-screen');
    setTimeout(function() {
        loadingScreen.classList.add('hidden');
    }, 500); // Tiempo de espera antes de ocultar la pantalla de carga
});
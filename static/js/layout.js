document.addEventListener('DOMContentLoaded', function() {
    const userIcon = document.getElementById('user-icon');
    const sideMenu = document.getElementById('side-menu');
    const closeBtn = document.getElementById('close-btn');

    // Función para abrir el menú lateral
    function openSideMenu() {
        sideMenu.style.width = '300px';
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

    // Evitar que el clic dentro del menú cierre el menú
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
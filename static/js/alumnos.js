// Función para alternar la visibilidad de la contraseña
function togglePasswordVisibility() {
    var passwordInput = document.getElementById('contraseña');
    var toggleIcon = document.getElementById('toggle-password');

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.add('active');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('active');
    }
}

// Asignar evento al ícono de "ojo" para alternar la visibilidad de la contraseña
document.getElementById('toggle-password').addEventListener('click', togglePasswordVisibility);

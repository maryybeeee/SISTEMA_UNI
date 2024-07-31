function eliminarDato(event, id, columna) {
    event.preventDefault();
    const confirmation = confirm("¿Desea eliminar este dato?");
    if (confirmation) {
        window.location.href = '/eliminar_dato/' + id + '/' + columna;
    }
}
function vaciarDato(noControl, year) {
    const confirmation = confirm("¿Desea vaciar el contenido de esta columna?");
    if (confirmation) {
        window.location.href = '/vaciar_dato/' + noControl + '/' + year;
    }
}
// ==========================================
// TEMPORIZADOR DE INACTIVIDAD (5 minutos)
// ==========================================
const TIEMPO_INACTIVIDAD_MS = 5 * 60 * 1000;   // 5 min -> cierre automatico
const TIEMPO_AVISO_MS = 4 * 60 * 1000;         // 4 min -> aviso previo

let timerCierre = null;
let timerAviso = null;
let chatCerrado = false;

// Elementos del DOM
const avisoInactividad = document.getElementById('aviso-inactividad');
const btnReiniciar = document.getElementById('btn-reiniciar');
const formChatInactividad = document.getElementById('form-chat');
const inputMsgInactividad = document.getElementById('input-msg');
const btnEnviarInactividad = document.getElementById('btn-enviar');
const mensajesDivInactividad = document.getElementById('mensajes');

// Reinicia ambos temporizadores (borra los anteriores y crea nuevos)
function reiniciarTemporizadorInactividad() {
    if (chatCerrado) return;

    // Ocultar aviso si estaba visible
    if (avisoInactividad) avisoInactividad.style.display = 'none';

    // Borrar temporizadores anteriores (evita fugas de memoria)
    if (timerCierre) clearTimeout(timerCierre);
    if (timerAviso) clearTimeout(timerAviso);

    // Programar aviso a los 4 minutos
    timerAviso = setTimeout(() => {
        if (avisoInactividad) avisoInactividad.style.display = 'flex';
    }, TIEMPO_AVISO_MS);

    // Programar cierre a los 5 minutos
    timerCierre = setTimeout(() => {
        cerrarPorInactividad();
    }, TIEMPO_INACTIVIDAD_MS);
}

// Cierre general del chat (por inactividad o porque el bot ha decidido cerrar).
// mensaje: texto que ve el usuario; notificarBackend: true solo si el servidor
// todavia no ha cerrado la conversacion (caso de la inactividad).
function cerrarChat(mensaje, notificarBackend) {
    // Si ya se cerro, no repetir (evita doble ejecucion)
    if (chatCerrado) return;
    chatCerrado = true;

    // 0. Parar los temporizadores pendientes
    if (timerCierre) clearTimeout(timerCierre);
    if (timerAviso) clearTimeout(timerAviso);

    // 1. Mensaje del sistema en el chat
    const msgSistema = document.createElement('div');
    msgSistema.className = 'mensaje-grupo';
    msgSistema.innerHTML =
        `<p class="msg-sistema">${escaparHtml(mensaje)}</p>`;
    mensajesDivInactividad.insertBefore(msgSistema, mensajesDivInactividad.firstChild);
    mensajesDivInactividad.scrollTop = mensajesDivInactividad.scrollHeight;

    // 2. Bloquear formulario y ocultar aviso
    inputMsgInactividad.disabled = true;
    btnEnviarInactividad.disabled = true;
    inputMsgInactividad.placeholder = 'Conversación cerrada';
    if (avisoInactividad) avisoInactividad.style.display = 'none';

    // Ocultar el indicador de "escribiendo" por si estuviera visible
    const escribiendo = document.getElementById('escribiendo');
    if (escribiendo) escribiendo.style.display = 'none';

    // 3. Mostrar boton de reiniciar
    const contenedorReiniciar = document.getElementById('contenedor-reiniciar');
    if (contenedorReiniciar) contenedorReiniciar.style.display = 'block';

    // 4. Notificar al backend solo si hace falta (si no, ya esta cerrada alla)
    if (notificarBackend) cerrarConversacionEnBackend();
}

// Cierre automatico por inactividad (el servidor aun no sabe que la cerramos)
function cerrarPorInactividad() {
    cerrarChat('La conversación se ha cerrado automáticamente por 5 minutos de inactividad.', true);
}

// Notifica al servidor que la conversacion se cierra
async function cerrarConversacionEnBackend() {
    // Usamos la variable global de ajax_chat.js (se actualiza al crear la conversacion
    // en esta sesion) y como respaldo el atributo data-conversacion del formulario.
    let token = '';
    if (typeof conversacionId !== 'undefined') token = conversacionId;
    if (!token) token = formChatInactividad.dataset.conversacion;
    if (!token) return;

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    try {
        await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=cerrar&conversacion=${token}`,
        });
    } catch (err) {
        console.error('Error cerrando conversacion:', err);
    }
}

// Reiniciar el chat (boton "Nueva conversacion")
if (btnReiniciar) {
    btnReiniciar.addEventListener('click', () => {
        // Limpiar estado
        chatCerrado = false;

        // Limpiar el token de la conversacion vieja (variables globales de ajax_chat.js)
        if (typeof conversacionId !== 'undefined') conversacionId = '';
        if (typeof ultimoMensajeId !== 'undefined') ultimoMensajeId = 0;
        if (typeof esperandoRespuesta !== 'undefined') esperandoRespuesta = false;

        // Limpiar mensajes anteriores
        mensajesDivInactividad.querySelectorAll('.mensaje-grupo, .msg-sistema').forEach(el => el.remove());

        // Restaurar mensaje de bienvenida
        const bienvenida = document.createElement('div');
        bienvenida.className = 'mensaje-grupo mensaje-grupo--bot';
        bienvenida.id = 'bienvenida-inicial';
        bienvenida.innerHTML = '<p class="msg-bot">Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?</p>';
        mensajesDivInactividad.insertBefore(bienvenida, mensajesDivInactividad.firstChild);

        // Reactivar formulario
        inputMsgInactividad.disabled = false;
        btnEnviarInactividad.disabled = false;
        inputMsgInactividad.placeholder = 'Escribe un mensaje';

        // Ocultar boton reiniciar
        const contenedorReiniciar = document.getElementById('contenedor-reiniciar');
        if (contenedorReiniciar) contenedorReiniciar.style.display = 'none';

        // Avisar al padre para que borre el token guardado
        window.parent.postMessage({ tipo: 'chatbot:token', token: '' }, '*');

        // Limpiar atributo data-conversacion para que se cree una nueva
        formChatInactividad.dataset.conversacion = '';

        // Reiniciar temporizador
        reiniciarTemporizadorInactividad();
        inputMsgInactividad.focus();
    });
}

// Evento: el usuario escribe -> reinicia temporizador
inputMsgInactividad.addEventListener('input', reiniciarTemporizadorInactividad);

// Iniciar el temporizador al cargar la pagina
reiniciarTemporizadorInactividad();
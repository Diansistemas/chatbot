const formChat = document.getElementById('form-chat');
const inputMsg = document.getElementById('input-msg');
const btnEnviar = document.getElementById('btn-enviar');
const mensajesDiv = document.getElementById('mensajes');
const escribiendoDiv = document.getElementById('escribiendo');

// Cada cuánto preguntamos al servidor si el bot ya ha respondido (ms)
const INTERVALO_POLLING_MS = 2000;
// Errores de red seguidos que toleramos en el polling antes de rendirnos
const MAX_ERRORES_POLLING = 5;

// Identificador de la conversación actual. Viene del atributo data-conversacion del <form>
let conversacionId = formChat.dataset.conversacion || '';

// Id del último mensaje que hay pintado en pantalla. El polling lo usa para pedir solo lo que sea posterior.
let ultimoMensajeId = formChat.dataset.ultimoMensaje || 0;

// True mientras estamos esperando (haciendo polling) la respuesta del bot
let esperandoRespuesta = false;
let erroresPolling = 0;

// Token CSRF necesario para que Django acepte las peticiones POST por fetch
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Si ya había una conversación guardada (usuario recurrente), avisamos a la página padre del iframe para que la guarde en su localStorage
if (conversacionId) {
    window.parent.postMessage({ tipo: 'chatbot:token', token: conversacionId }, '*');
}

// Bloquea el formulario mientras el bot responde.
function bloquearFormulario() {
    btnEnviar.disabled = true;
    inputMsg.disabled = true;
}

// Reactiva el formulario y oculta el indicador de escribiendo del bot.
function desbloquearFormulario() {
    btnEnviar.disabled = false;
    inputMsg.disabled = false;
    escribiendoDiv.style.display = 'none';
    inputMsg.focus();
}

// Pinta un mensaje del bot. La hora es opcional (el mensaje de error local no la tiene).
// Se inserta justo después del indicador de escribiendo, igual que el resto de mensajes.
function pintarMensajeBot(texto, hora) {
    escribiendoDiv.insertAdjacentHTML('afterend', `
        <div class="mensaje-grupo mensaje-grupo--bot">
            <p class="msg-bot">${escaparHtml(texto)}</p>
            ${hora ? `<small class="msg-hora">${hora}</small>` : ''}
        </div>
    `);
    mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
}

// Pinta un mensaje del usuario.
function pintarMensajeUsuario(texto, hora) {
    escribiendoDiv.insertAdjacentHTML('afterend', `
        <div class="mensaje-grupo mensaje-grupo--user">
            <p class="msg-user">${escaparHtml(texto)}</p>
            <small class="msg-hora">${hora}</small>
        </div>
    `);
    mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
}

// El bot todavía está generando una respuesta que este navegador no está esperando por fetch
// (típicamente porque el usuario recargó la página a mitad de respuesta).
// Bloqueamos el formulario, mostramos "escribiendo" y preguntamos al servidor cada poco tiempo
// hasta que la respuesta esté guardada.
function esperarRespuesta() {
    if (esperandoRespuesta) return;
    esperandoRespuesta = true;
    erroresPolling = 0;
    bloquearFormulario();
    escribiendoDiv.style.display = 'flex';
    mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
    consultarEstado();
}

// Termina la espera y devuelve el chat a su estado normal.
function terminarEspera() {
    esperandoRespuesta = false;
    desbloquearFormulario();
}

// Una vuelta de polling: pide al servidor los mensajes del bot nuevos y si sigue respondiendo.
async function consultarEstado() {
    try {
        const resp = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=estado&conversacion=${conversacionId}&desde_id=${ultimoMensajeId}`,
        });

        if (!resp.ok) {
            const textoError = await resp.text();
            console.error(`Error ${resp.status}:`, textoError);
            throw new Error(`HTTP ${resp.status}`);
        }

        const data = await resp.json();
        erroresPolling = 0;

        // Pintamos en orden las respuestas nuevas del bot (normalmente será una).
        for (const mensaje of data.mensajes) {
            pintarMensajeBot(mensaje.texto, mensaje.hora);
            ultimoMensajeId = mensaje.id;
        }

        // Si el bot ya no está respondiendo se vuelve a permitir escribir.
        if (!data.esperando) {
            terminarEspera();
            return;
        }
    } catch (err) {
        console.error(err);
        erroresPolling++;
        // Si el servidor no responde varias veces seguidas dejamos de esperar y avisamos.
        // Si el bot siguiera generando, el servidor rechazará el siguiente mensaje (409) y volveremos a esperar.
        if (erroresPolling >= MAX_ERRORES_POLLING) {
            pintarMensajeBot('Ha habido un error, inténtalo de nuevo.');
            terminarEspera();
            return;
        }
    }

    setTimeout(consultarEstado, INTERVALO_POLLING_MS);
}

// Se ejecuta cada vez que el usuario envía el formulario, contiene la lógica del chat.
formChat.addEventListener('submit', async function (evento) {
    //Evita que el formulario recargue la página.
    evento.preventDefault();

    //Mientras el bot está respondiendo no se puede enviar nada.
    if (esperandoRespuesta) return;

    const texto = inputMsg.value.trim();
    if (!texto) return;

    //Se limpia el input de texto y se bloquea mientras el bot hace la respuesta.
    inputMsg.value = '';
    bloquearFormulario();

    try {
        // Se crea el mensaje del usuario y se manda al servidor
        const respUsuario = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=usuario&texto=${encodeURIComponent(texto)}&conversacion=${conversacionId}`,
        });

        //El servidor rechaza el mensaje (409) si el bot aún no ha respondido al anterior
        //(por ejemplo desde otra pestaña). Devolvemos el texto al input y esperamos a que termine.
        if (respUsuario.status === 409) {
            inputMsg.value = texto;
            esperarRespuesta();
            return;
        }

        //Si hay fallo en la respuesta del usuario lo muestra en consola y salta el catch
        if (!respUsuario.ok) {
            const textoError = await respUsuario.text();
            console.error(`Error ${respUsuario.status}:`, textoError);
            throw new Error(`HTTP ${respUsuario.status}`);
        }

        const dataUsuario = await respUsuario.json();

        //Si antes no había conversación la view genera una nueva y la página padre del widget almacena su token.
        if (!conversacionId) {
            conversacionId = dataUsuario.conversacion;
            window.parent.postMessage({ tipo: 'chatbot:token', token: conversacionId }, '*');
        }

        //Si es el primer mensaje de la conversación, se pinta el primer mensaje del bot.
        if (dataUsuario.bienvenida) {
            const bienvenidaEstatica = document.getElementById('bienvenida-inicial');
            if (bienvenidaEstatica) bienvenidaEstatica.remove();

            pintarMensajeBot(dataUsuario.bienvenida.texto, dataUsuario.bienvenida.hora);
        }

        //Aqui se pinta el mensaje de usuario en el chat (y se hace scroll automático).
        pintarMensajeUsuario(texto, dataUsuario.hora_usuario);
        ultimoMensajeId = dataUsuario.mensaje_id;

        //Mostramos el mensaje animado de escribiendo del bot.
        escribiendoDiv.style.display = 'flex';

        // Se pide la respuesta del bot para el mensaje introducido.
        const respBot = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=bot&mensaje_id=${dataUsuario.mensaje_id}&conversacion=${conversacionId}`,
        });

        //Si hay algun error en la respuesta del bot muestra el error en consola y salta el catch.
        if (!respBot.ok) {
            const textoError = await respBot.text();
            console.error(`Error ${respBot.status}:`, textoError);
            throw new Error(`HTTP ${respBot.status}`);
        }

        const dataBot = await respBot.json();

        //Se pinta en pantalla la respuesta del bot.
        pintarMensajeBot(dataBot.bot, dataBot.hora_bot);
        ultimoMensajeId = dataBot.mensaje_id;

    } catch (err) {
        //Si se encuentra algun error se muestran los errores correspondientes
        //Ademas el usuario verá un mensaje del bot indicando que ha ocurrido un error.
        console.error(err);
        pintarMensajeBot('Ha habido un error, inténtalo de nuevo.');
    } finally {
        //Da igual lo que ocurra siempre se ejecuta, salvo que hayamos pasado a modo espera (polling),
        //en cuyo caso será terminarEspera() quien reactive el formulario.
        if (!esperandoRespuesta) {
            desbloquearFormulario();
        }
    }
});

// Escapa HTML antes de insertarlo en el DOM, para evitar XSS si el texto
// del usuario o del bot contiene etiquetas como <script>
function escaparHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}

// Si al cargar la página el servidor dice que el bot todavía está respondiendo
// (el usuario recargó a mitad de respuesta), nos ponemos a esperar la respuesta.
if (formChat.dataset.esperando === 'true') {
    esperarRespuesta();
}
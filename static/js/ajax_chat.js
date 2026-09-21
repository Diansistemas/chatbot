const formChat = document.getElementById('form-chat');
const inputMsg = document.getElementById('input-msg');
const btnEnviar = document.getElementById('btn-enviar');
const mensajesDiv = document.getElementById('mensajes');
const escribiendoDiv = document.getElementById('escribiendo');

// Identificador de la conversación actual. Viene del atributo data-conversacion del <form>
let conversacionId = formChat.dataset.conversacion || '';

// Token CSRF necesario para que Django acepte las peticiones POST por fetch
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Si ya había una conversación guardada (usuario recurrente), avisamos a la página padre del iframe para que la guarde en su localStorage
if (conversacionId) {
    window.parent.postMessage({ tipo: 'chatbot:token', token: conversacionId }, '*');
}

// Se ejecuta cada vez que el usuario envía el formulario, contiene la lógica del chat.
formChat.addEventListener('submit', async function (evento) {
    //Evita que el formulario recargue la página.
    evento.preventDefault();
    const texto = inputMsg.value.trim();
    if (!texto) return;

    //Se limpia el input de texto y se bloquea mientras el bot hace la respuesta.
    inputMsg.value = '';
    btnEnviar.disabled = true;
    inputMsg.disabled = true;

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

            escribiendoDiv.insertAdjacentHTML('afterend', `
                <div class="mensaje-grupo mensaje-grupo--bot">
                    <p class="msg-bot">${escaparHtml(dataUsuario.bienvenida.texto)}</p>
                    <small class="msg-hora">${dataUsuario.bienvenida.hora}</small>
                </div>
            `);
        }

        //Aqui se pinta el mensaje de usuario en el chat.
        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--user">
                <p class="msg-user">${escaparHtml(texto)}</p>
                <small class="msg-hora">${dataUsuario.hora_usuario}</small>
            </div>
        `);
        //Se hace scroll automático para ver el ultimo mensaje.
        mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
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
        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--bot">
                <p class="msg-bot">${escaparHtml(dataBot.bot)}</p>
                <small class="msg-hora">${dataBot.hora_bot}</small>
            </div>
        `);

    } catch (err) {
        //Si se encuentra algun error se muestran los errores correspondientes
        //Ademas el usuario verá un mensaje del bot indicando que ha ocurrido un error.
        console.error(err);
        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--bot">
                <p class="msg-bot">Ha habido un error, inténtalo de nuevo.</p>
            </div>
        `);
    } finally {
        //Da igual lo que ocurra siempre se ejecuta y reactiva el formulario y se oculta el indicador de escribiendo del bot.
        btnEnviar.disabled = false;
        inputMsg.disabled = false;
        escribiendoDiv.style.display = 'none';
        inputMsg.focus();
    }
});

// Escapa HTML antes de insertarlo en el DOM, para evitar XSS si el texto
// del usuario o del bot contiene etiquetas como <script>
function escaparHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}
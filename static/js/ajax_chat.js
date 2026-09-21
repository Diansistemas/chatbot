const formChat = document.getElementById('form-chat');
const inputMsg = document.getElementById('input-msg');
const btnEnviar = document.getElementById('btn-enviar');
const mensajesDiv = document.getElementById('mensajes');
const escribiendoDiv = document.getElementById('escribiendo');
let conversacionId = formChat.dataset.conversacion || '';
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

if (conversacionId) {
    window.parent.postMessage({ tipo: 'chatbot:token', token: conversacionId }, '*');
}

formChat.addEventListener('submit', async function (e) {
    e.preventDefault();
    const texto = inputMsg.value.trim();
    if (!texto) return;

    inputMsg.value = '';
    btnEnviar.disabled = true;
    inputMsg.disabled = true;

    try {
        // Se crea el mensaje del usuario y se pinta en pantalla
        const respUsuario = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=usuario&texto=${encodeURIComponent(texto)}&conversacion=${conversacionId}`,
        });

        if (!respUsuario.ok) {
            const textoError = await respUsuario.text();
            console.error(`Error ${respUsuario.status}:`, textoError);
            throw new Error(`HTTP ${respUsuario.status}`);
        }

        const dataUsuario = await respUsuario.json();

        if (!conversacionId) {
            conversacionId = dataUsuario.conversacion;
            window.parent.postMessage({ tipo: 'chatbot:token', token: conversacionId }, '*');
        }

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

        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--user">
                <p class="msg-user">${escaparHtml(texto)}</p>
                <small class="msg-hora">${dataUsuario.hora_usuario}</small>
            </div>
        `);
        mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
        escribiendoDiv.style.display = 'flex';

        // Se pide la respuesta del bot para el mensaje
        const respBot = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `accion=bot&mensaje_id=${dataUsuario.mensaje_id}&conversacion=${conversacionId}`,
        });

        if (!respBot.ok) {
            const textoError = await respBot.text();
            console.error(`Error ${respBot.status}:`, textoError);
            throw new Error(`HTTP ${respBot.status}`);
        }

        const dataBot = await respBot.json();

        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--bot">
                <p class="msg-bot">${escaparHtml(dataBot.bot)}</p>
                <small class="msg-hora">${dataBot.hora_bot}</small>
            </div>
        `);
    } catch (err) {
        console.error(err);
        escribiendoDiv.insertAdjacentHTML('afterend', `
            <div class="mensaje-grupo mensaje-grupo--bot">
                <p class="msg-bot">Ha habido un error, inténtalo de nuevo.</p>
            </div>
        `);
    } finally {
        btnEnviar.disabled = false;
        inputMsg.disabled = false;
        escribiendoDiv.style.display = 'none';
        inputMsg.focus();
    }
});
function escaparHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}
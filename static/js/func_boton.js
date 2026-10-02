//Función que abre el panel del chat
function abrir() {
    document.getElementById('chat-btn').style.display = 'none';
    const panel = document.getElementById('chat-panel');
    panel.style.display = 'flex';
    requestAnimationFrame(() => panel.classList.add('abierto'));
    window.parent.postMessage('chatbot:open', '*');
}
//Función que cierra el panel del chat y vuelve al botón
function cerrar() {
    const panel = document.getElementById('chat-panel');
    panel.classList.remove('abierto');
    panel.addEventListener('transitionend', function ocultar() {
        panel.style.display = 'none';
        document.getElementById('chat-btn').style.display = 'flex';
        panel.removeEventListener('transitionend', ocultar);
    });
    window.parent.postMessage('chatbot:close', '*');
}
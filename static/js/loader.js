(function () {
  // Origen del chatbot: se deduce de la propia URL con la que se carga este script,
  // asi funciona en cualquier dominio (WordPress, prod, local...) sin tocar nada.
  // Personalizable: <script data-url="https://chat.tudominio.com" src=".../loader.js"></script>
  var actual = document.currentScript;
  var origen = 'http://localhost:8000'; // fallback para uso local
  if (actual && actual.src) {
    try { origen = new URL(actual.src).origin; } catch (e) { /* se queda el fallback */ }
  }
  if (actual && actual.dataset && actual.dataset.url) {
    try { origen = new URL(actual.dataset.url).origin; } catch (e) { /* valor invalido, ignorado */ }
  }

  //Enlace al css para el apartado visual del iframe
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = origen + '/static/css/loader.css';
  document.head.appendChild(link);

  // Recupera el token guardado de una visita anterior (si lo hay)
  var tokenGuardado = localStorage.getItem('chatbot_conversacion_token');
  var src = origen + '/chat/';
  if (tokenGuardado) {
    src += '?conversacion=' + encodeURIComponent(tokenGuardado);
  }

  //Crea el objeto iframe para la pagina
  var iframe = document.createElement('iframe');
  iframe.src = src;
  iframe.id = 'mi-chatbot-iframe';
  iframe.title = 'Chatbot Dian Sistemas';
  iframe.className = 'chatbot-iframe';
  document.body.appendChild(iframe);

  //Función que da la lógica de abrir, cerrar y comprobar si hay una conversación abierta para el botón del iframe.
  window.addEventListener('message', function (event) {
    if (event.data === 'chatbot:open') {
      iframe.classList.add('chatbot-iframe--abierto');
    } else if (event.data === 'chatbot:close') {
      iframe.classList.remove('chatbot-iframe--abierto');
    } else if (event.data && event.data.tipo === 'chatbot:token') {
      localStorage.setItem('chatbot_conversacion_token', event.data.token);
    }
  });
})();

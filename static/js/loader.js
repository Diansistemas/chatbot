(function () {
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'http://localhost:8000/static/css/loader.css';
  document.head.appendChild(link);

  // Recupera el token guardado de una visita anterior (si lo hay)
  var tokenGuardado = localStorage.getItem('chatbot_conversacion_token');
  var src = 'http://localhost:8000/chat/';
  if (tokenGuardado) {
    src += '?conversacion=' + encodeURIComponent(tokenGuardado);
  }

  var iframe = document.createElement('iframe');
  iframe.src = src;
  iframe.id = 'mi-chatbot-iframe';
  iframe.title = 'Chatbot Dian Sistemas';
  iframe.className = 'chatbot-iframe';
  document.body.appendChild(iframe);

  window.addEventListener('message', function (event) {
    if (event.data === 'chatbot:open') {
      iframe.classList.add('chatbot-iframe--abierto');
    } else if (event.data === 'chatbot:close') {
      iframe.classList.remove('chatbot-iframe--abierto');
    } else if (event.data && event.data.tipo === 'chatbot:token') {
      localStorage.setItem('chatbot_conversacion_token', event.data.token);   // NUEVO
    }
  });
})();
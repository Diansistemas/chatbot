(function () {
  //Conexión con el css de loader
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'http://localhost:8000/static/css/loader.css';
  document.head.appendChild(link);

  //Creación del contenedor iframe
  var iframe = document.createElement('iframe');
  iframe.src = 'http://localhost:8000/chat/';
  iframe.id = 'mi-chatbot-iframe';
  iframe.title = 'Chatbot Dian Sistemas';
  iframe.className = 'chatbot-iframe';
  document.body.appendChild(iframe);

  //Lógica de abrir y cerrar el chat
  window.addEventListener('message', function (event) {
    if (event.data === 'chatbot:open') {
      iframe.classList.add('chatbot-iframe--abierto');
    } else if (event.data === 'chatbot:close') {
      iframe.classList.remove('chatbot-iframe--abierto');
    }
  });
})();
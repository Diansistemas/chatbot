(function () {
  var iframe = document.createElement('iframe');
  iframe.src = 'http://localhost:8000/chat/';
  iframe.id = 'mi-chatbot-iframe';
  iframe.title = 'Chatbot Dian Sistemas';
  iframe.style.cssText =
    'position:fixed;bottom:20px;right:20px;width:56px;height:56px;' +
    'border:none;border-radius:50%;z-index:999999;' +
    'box-shadow:0 4px 12px rgba(0,0,0,.15);' +
    'transition:width .3s ease, height .3s ease, border-radius .3s ease;';
  document.body.appendChild(iframe);

  window.addEventListener('message', function (event) {
    if (event.data === 'chatbot:open') {
      iframe.style.width = '360px';
      iframe.style.height = '560px';
      iframe.style.borderRadius = '16px';
    } else if (event.data === 'chatbot:close') {
      iframe.style.width = '56px';
      iframe.style.height = '56px';
      iframe.style.borderRadius = '50%';
    }
  });
})();
# Chatbot
Chatbot con IA para uso comercial de Dian Sistemas

## Funciones implementadas
- **Estructura basica** — Estructuras basica de la apliación
- **Generacion de NLP** — Generacion de los modelos ntl a traves del manage.py
- **Generacion de LLMs** — Generacion de los modelos llms a traves del manage.py
- **Almacenaje de datos basicos** — Creacion de las entradas en la base de datos a traves del manage.py
- **Chatbot** — Un chatbot funcional que ajusta el modelo usado dependiendo de la intencion del usuario
  
## Funciones no implementadas
- **Notificaciones** — Creacion y envio de resumenes de las conversaciones relevantes
- **Entrenamiento de modelos** — Ajustes a los modelos y entrenamiento con datos relevantes
- **Docker** — Dockerizar el proyecto
- **Servidor** — Hosteo del widget en un servidor
- **Cerrar conversación** — Donde cerramos una conversación
- **Pequeños cambios** — Cambios TODO en varias partes del código
  
## Estructura del proyecto 
Este projecto es una aplicacion web de Django con la siguiente estructura:
- **Core** — La funcionalidad en torno al chatbot
    - **Mixins** — Ajustes de permsiso web
    - **Acceso** — Acceso a los modelos
- **Entrenamiento** — App centrada en el entrenamiento de los modelos
    - **Datos** — CSV que continene los datos iniciales de la base de datos
    - **LLMs** — Directorio para los Modelfile para los llms
    - **SpaCy** — Directorio para la totalidad del nlp
    - **Management** — Directorio de los comandos personalizados para la configuracion inicial de la app
- **Chat** — App encargada de la gestion de los chats
- **Notificaciones** — App encargadsa de las notificaciones
- **Docs** — Documentacion adicional

## Tech Stack
- **Backend:** Python, Django
- **Database:** SQLite
- **Frontend:** Bootstrap5
- **NLP:** spaCy
- **LLM:** Ollama, Llama

## Creditos
- Victor Herrero
- Adrian Salas

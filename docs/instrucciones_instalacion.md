# Guía de Instalación - Chatbot DianSistemas

Guía completa para instalar y configurar el entorno de desarrollo del chatbot.

---

## Prerrequisitos

| Herramienta | Versión mínima | Verificación |
|-------------|----------------|--------------|
| **Git** | 2.30+ | `git --version` |
| **Python** | 3.10+ | `python --version` |
| **pip** | 21+ | `pip --version` |
| **Ollama** | 0.1+ (opcional) | `ollama --version` |

> **Nota**: Ollama es necesario para los modelos LLM. Instálalo desde [ollama.ai](https://ollama.ai).

---

## 1. Clonar el repositorio

```bash
git clone https://github.com/josecursoprogramacion-coder/Chatbot.git
cd Chatbot
```

---

## 2. Crear y activar entorno virtual

### Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Windows (CMD)
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

> Verifica que el prompt cambie a `(venv) ...`

---

## 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configurar variables de entorno (`.env`)

Copia el archivo de ejemplo y edítalo:

```bash
# Linux/macOS
cp .env.example .env
# Windows
copy .env.example .env
```

Edita `.env` con tus valores:

```ini
# Django
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True

# Dominios permitidos (para iframe embedding)
DOMINIOS_PERMITIDOS=https://diansitemas.com, http://localhost:8000

# Base de datos
# DATABASE_URL=sqlite:///db.sqlite3  (por defecto)

# Ollama
OLLAMA_HOST=http://localhost:11434

# Email (smtp4dev local)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=127.0.0.1
EMAIL_PORT=25
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=False
RESUMEN_EMAIL_DESTINATARIOS=admin@diansistemas.com
```

> **Importante**: En producción usa un gestor de secretos y `DEBUG=False`.

---

## 5. Aplicar migraciones

```bash
python manage.py migrate
```

---

## 6. (Opcional) Crear superusuario para admin

```bash
python manage.py createsuperuser
```

---

## 6. Cargar datos iniciales

Carga intenciones, etiquetas, servicios, ejemplos NLP y modelfiles:

```bash
python manage.py cargar_datos_iniciales
```

---

## 7. Generar y entrenar modelo spaCy

### 7.1 Generar datos de entrenamiento (.spacy)

```bash
python manage.py generar_nlp
```

Esto crea:
- `entrenamiento/spacy/train.spacy` (80%)
- `entrenamiento/spacy/dev.spacy` (20%)

### 7.2 Entrenar modelo

```bash
python -m spacy train ./entrenamiento/spacy/config.cfg \
  --paths.train ./entrenamiento/spacy/train.spacy \
  --paths.dev ./entrenamiento/spacy/dev.spacy \
  --output ./entrenamiento/spacy/modelo
```

> **Tiempo estimado**: 5-15 min en CPU. El mejor modelo se guarda en `modelo/model-best/`.

---

## 8. Instalar y configurar Ollama (LLM)

### 8.1 Instalar Ollama

```bash
# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Windows
# Descargar desde https://ollama.ai/download
```

### 8.2 Iniciar servidor Ollama

```bash
ollama serve
```

### 8.3 Descargar modelo base

```bash
ollama pull llama3.2
```

### 8.4 Generar y crear Modelfiles

```bash
python manage.py generar_modelfiles
python manage.py generar_modelfiles --crear
```

Esto crea modelos por intención:
- `chatbot-compra`
- `chatbot-consulta`  
- `chatbot-otro`
- Variantes por dominio: `chatbot-localhost-compra`, etc.

---

## 9. (Opcional) smtp4dev para testing de emails

```bash
# Ejecutar (puerto web cambia cada arranque)
.\entrenamiento\smtp4dev\Rnwood.Smtp4dev.Desktop.exe

# Ver correos en http://127.0.0.1:<puerto_web>
# SMTP en 127.0.0.1:25 (sin TLS)
```

---

## 10. Arrancar servidor de desarrollo

```bash
python manage.py runserver 127.0.0.1:8000
```

Abre en navegador:
- **Chat**: http://127.0.0.1:8000/chat/
- **Admin**: http://127.0.0.1:8000/admin/

---

## Instalación automática

Usa los scripts proporcionados:

### Windows
```powershell
.\install.ps1                    # Completa
.\install.ps1 -UseDocker         # Con Docker
.\install.ps1 -SkipNlpTrain      # Sin entrenar NLP
```

### Linux/macOS
```bash
chmod +x install.sh
./install.sh                     # Completa
./install.sh --use-docker        # Con Docker
./install.sh --skip-nlp-train    # Sin entrenar NLP
./install.sh --help              # Ver opciones
```

---

## Verificación rápida

```bash
# Verificar NLP
python -c "
import spacy
nlp = spacy.load('entrenamiento/spacy/modelo/model-best')
doc = nlp('quiero un presupuesto')
print('Intención:', max(doc.cats, key=doc.cats.get))
"

# Verificar Ollama
ollama list

# Verificar modelos creados
ollama list | grep chatbot
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `spacy` no encuentra modelo | Verifica `SPACY_MODEL_PATH` en `.env` |
| Ollama connection refused | Inicia `ollama serve` |
| Puerto 8000 ocupado | `python manage.py runserver 8001` |
| Error migraciones | `python manage.py migrate --fake-initial` |
| Modelo spaCy no carga | Reentrena: `python manage.py generar_nlp && python -m spacy train...` |

---

## Próximos pasos

- 📖 [Dockerización](dockerizacion.md) - Despliegue con contenedores
- 🧠 [Configuración de entrenamiento](configuracion_entrenamiento.md) - Personalizar modelos
- 🔒 [Checklist producción](../README.md#checklist-producción-seguridad) - Seguridad en producción
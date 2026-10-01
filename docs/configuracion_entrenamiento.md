# Configuración de Entrenamiento - Chatbot DianSistemas

Guía completa para entender, personalizar y reentrenar los modelos del chatbot.

---

## Visión general del pipeline de entrenamiento

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   Datos CSV     │────▶│  Django Models   │────▶│  .spacy (train/    │
│  (entrenamiento/│     │  (EjemploNLP,    │     │   dev.spacy)       │
│   datos/nlp.csv)│     │   Intencion,     │     │                     │
└─────────────────┘     │   EtiquetaEntidad)│     └────────┬───────────┘
                        └──────────────────┘              │
                                                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Modelos LLM    │     │  Modelo spaCy    │◀────│  spaCy train       │
│  (Ollama)       │     │  (textcat + NER) │     │  config.cfg        │
└─────────────────┘     └──────────────────┘     └────────────────────┘
```

---

## 1. Datos de entrenamiento (CSV)

### Archivo principal: `entrenamiento/datos/nlp.csv`

Formato: `texto;intencion;origen;entidades`

```csv
texto;intencion;origen;entidades
"Quiero un presupuesto";compra;manual;
"Mi empresa tiene 10 trabajadores";compra;manual;SERVICIO:auditoria|EMPRESA:mi empresa
"Tengo un error al instalar";consulta_tecnica;manual;
"Quiero hablar con un agente";contactar_humano;manual;
"Hola buenos días";otro;manual;
```

### Campos

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `texto` | Texto del usuario (obligatorio) | "Quiero un presupuesto" |
| `intencion` | Categoría (compra, consulta_tecnica, contactar_humano, cerrar, confirmacion, otro) | compra |
| `origen` | Fuente: `manual` (humano), `chatbot` (auto), `promovido` | manual |
| `entidades` | Anotaciones `ETIQUETA:texto` separadas por `\|` | `SERVICIO:auditoria\|EMPRESA:mi empresa` |

### Añadir nuevos ejemplos

```bash
# Editar CSV directamente
nano entrenamiento/datos/nlp.csv

# O usar Django shell
python manage.py shell -c "
from entrenamiento.models import EjemploNLP, Intencion
EjemploNLP.objects.create(
    texto='Nuevo ejemplo de compra',
    intencion=Intencion.objects.get(nombre='compra'),
    origen='manual'
)
"
```

### Reimportar datos

```bash
# Limpiar y recargar todo
python manage.py cargar_nlp --limpiar

# Solo añadir (sin limpiar)
python manage.py cargar_nlp
```

---

## 2. Intenciones y Etiquetas

### Intenciones configuradas (`entrenamiento/datos/intenciones.csv`)

| Intención | Descripción | Activa |
|-----------|-------------|--------|
| `compra` | Usuario quiere comprar/contratar | ✅ |
| `consulta_tecnica` | Soporte técnico, errores, instalación | ✅ |
| `contactar_humano` | Quiere hablar con agente | ✅ |
| `cerrar` | Despedida, fin de conversación | ✅ |
| `confirmacion` | Acepta presupuesto/condiciones | ✅ |
| `otro` | Saludos, info general, otros | ✅ |

### Etiquetas de entidades (`entrenamiento/datos/etiquetas.csv`)

| Etiqueta | Descripción |
|----------|-------------|
| `SERVICIO` | Nombre del servicio/producto |
| `EMPRESA` | Nombre de la empresa del cliente |
| `PRECIO` | Montos, presupuestos, costes |
| `EMPLEADOS` | Número de trabajadores |
| `SECTOR` | Sector de actividad |
| `CONTACTO` | Email, teléfono, nombre contacto |
| `UBICACION` | Dirección, ciudad |

---

## 3. Generar datos .spacy

### Comando

```bash
python manage.py generar_nlp [--dev-ratio 0.2]
```

### Qué hace

1. Lee todos `EjemploNLP` de la BD
2. Crea `Doc` de spaCy con:
   - **textcat**: `cats = {intencion: 1.0, otras: 0.0}` (exclusive_classes=True)
   - **NER**: `doc.ents` con spans de entidades
3. Split determinístico train/dev (hash del texto)
4. Guarda `train.spacy` y `dev.spacy` en `entrenamiento/spacy/`

### Estadísticas de salida

```
train.spacy: 232 ejemplos
  intent:compra: 38
  intent:consulta_tecnica: 48
  intent:contactar_humano: 46
  intent:confirmacion: 34
  intent:cerrar: 31
  intent:otro: 35
  ent:SERVICIO: 70
  ent:PRECIO: 44
  ...
dev.spacy: 63 ejemplos
  ...
```

---

## 4. Configuración spaCy (`entrenamiento/spacy/config.cfg`)

### Pipeline actual

```ini
[nlp]
lang = "es"
pipeline = ["tok2vec", "textcat"]
batch_size = 1000

[components.textcat]
factory = "textcat"
threshold = 0.0
exclusive_classes = true

[components.textcat.model]
@architectures = "spacy.TextCatEnsemble.v2"

[components.textcat.model.tok2vec]
@architectures = "spacy.Tok2VecListener.v1"
width = 256

[components.textcat.model.linear_model]
@architectures = "spacy.TextCatBOW.v3"
exclusive_classes = true
length = 262144
ngram_size = 1
```

### Vectores preentrenados

```ini
[paths]
vectors = "es_core_news_lg"  # Usa vectores de 500k palabras
```

### Hiperparámetros clave

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `max_steps` | 20000 | Pasos máximos (early stopping por patience) |
| `patience` | 1600 | Pasos sin mejora antes de parar |
| `eval_frequency` | 200 | Evaluar cada N pasos |
| `dropout` | 0.1 | Regularización |
| `learn_rate` | 0.001 | Adam optimizer |
| `batch_size` | 100 → 1000 (compounding) | Tamaño batch dinámico |

### Modificar hiperparámetros

Edita `entrenamiento/spacy/config.cfg` y reentrena:

```bash
# Forzar reentrenamiento
FORCE_TRAIN=1 python manage.py generar_nlp
python -m spacy train ./entrenamiento/spacy/config.cfg \
  --paths.train ./entrenamiento/spacy/train.spacy \
  --paths.dev ./entrenamiento/spacy/dev.spacy \
  --output ./entrenamiento/spacy/modelo
```

---

## 3. Entrenar modelo spaCy

### Comando completo

```bash
python -m spacy train ./entrenamiento/spacy/config.cfg \
  --paths.train ./entrenamiento/spacy/train.spacy \
  --paths.dev ./entrenamiento/spacy/dev.spacy \
  --output ./entrenamiento/spacy/modelo
```

### Salida esperada

```
E    #       LOSS TOK2VEC  LOSS TEXTCAT  CATS_SCORE  SCORE 
---  ------  ------------  ------------  ----------  ------
  0       0          0.00          0.14       21.11    0.21
 13     200         98.23          3.99       92.14    0.92
 33     400          0.97          0.03       91.94    0.92
...
500    20000         0.00          0.00       94.80    0.95
```

### Métricas clave

| Métrica | Objetivo | Descripción |
|---------|---------|-------------|
| `CATS_SCORE` | > 0.90 | Accuracy macro textcat |
| `SCORE` | > 0.90 | Score combinado |
| `LOSS TEXTCAT` | → 0 | Pérdida clasificación |

### Modelos generados

```
entrenamiento/spacy/modelo/
├── model-best/     # Mejor modelo (mayor CATS_SCORE)
│   ├── config.cfg
│   ├── meta.json
│   ├── tokenizer
│   ├── tok2vec
│   └── textcat
└── model-last/     # Último checkpoint
```

### Usar modelo entrenado

```python
import spacy
nlp = spacy.load("entrenamiento/spacy/modelo/model-best")

doc = nlp("Quiero un presupuesto para auditoría")
print(doc.cats)
# {'compra': 0.99, 'otro': 0.001, ...}
```

---

## 4. Configuración LLM (Ollama)

### Modelos por intención

| Intención | Modelo Ollama | Descripción |
|-----------|---------------|-------------|
| `compra` | `chatbot-compra` / `chatbot-{dominio}-compra` | Ventas, presupuestos |
| `consulta_tecnica` | `chatbot-consulta` / `chatbot-{dominio}-consulta` | Soporte técnico |
| `otro` | `chatbot-otro` / `chatbot-{dominio}-otro` | General, saludos |
| Resúmenes | `llama3.2` (base) | Resúmenes de compra |

### Modelfiles

Se generan automáticamente con:

```bash
python manage.py generar_modelfiles
python manage.py generar_modelfiles --crear
```

Estructura en `entrenamiento/llms/`:
```
entrenamiento/llms/
├── Modelfile.default.compra
├── Modelfile.default.consulta
├── Modelfile.default.otro
├── Modelfile.localhost.compra
├── Modelfile.localhost.consulta
└── Modelfile.localhost.otro
```

### Personalizar Modelfile

Edita las plantillas en `entrenamiento/llms/cabeceras/` y regenera:

```bash
python manage.py generar_modelfiles --crear
```

Ejemplo `Modelfile.default.compra`:
```
FROM llama3.2

SYSTEM "Eres un asistente de ventas de DianSistemas. Responde de forma profesional..."

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
```

---

## 5. Flujo completo de reentrenamiento

### Desde cero (datos nuevos)

```bash
# 1. Editar/añadir ejemplos en CSV
nano entrenamiento/datos/nlp.csv

# 2. Recargar en BD
python manage.py cargar_nlp --limpiar

# 3. Generar .spacy
python manage.py generar_nlp

# 4. Entrenar spaCy
python -m spacy train ./entrenamiento/spacy/config.cfg \
  --paths.train ./entrenamiento/spacy/train.spacy \
  --paths.dev ./entrenamiento/spacy/dev.spacy \
  --output ./entrenamiento/spacy/modelo

# 5. Regenerar modelos LLM
python manage.py generar_modelfiles --crear

# 6. Verificar
python -c "
import spacy
nlp = spacy.load('entrenamiento/spacy/modelo/model-best')
print('Test compra:', max(nlp('quiero presupuesto').cats, key=lambda x: nlp('quiero presupuesto').cats[x]))
"
```

### Solo añadir ejemplos (sin borrar existentes)

```bash
python manage.py cargar_nlp  # Sin --limpiar
python manage.py generar_nlp
python -m spacy train ...
python manage.py generar_modelfiles --crear
```

### Con Docker (automático)

```bash
# Forzar reentrenamiento completo
docker compose run --rm -e FORCE_TRAIN=1 -e FORCE_RELOAD=1 setup

# Solo reentrenar NLP (datos ya cargados)
docker compose run --rm -e FORCE_TRAIN=1 setup
```

---

## 6. Evaluación y testing

### Script de verificación (16 casos)

```bash
python pruebas/evaluacion/verificar_nlp.py entrenamiento/spacy/modelo/model-best
```

Casos de prueba:
- 5 compras (presupuesto, contratar, etc.)
- 4 otros (saludos)
- 3 cerrar (despedidas)
- 2 consulta_tecnica (error, instalación)
- 1 contactar_humano
- 1 confirmacion

**Objetivo**: ≥ 15/16 aciertos

### Evaluar solo textcat

```bash
python -m spacy evaluate \
  entrenamiento/spacy/modelo/model-best \
  entrenamiento/spacy/dev.spacy \
  --output metrics.json
```

---

## 6. Promover ejemplos del chat a entrenamiento

### Desde admin

1. Ve a `/admin/entrenamiento/analisis/`
2. Filtra por intención correcta
3. Acción: "Promover a ejemplo de entrenamiento"
4. Esto crea `EjemploNLP` con `origen="chatbot"`

### Desde código

```python
from core.models import promover_analisis_a_ejemplo
from entrenamiento.models import Analisis

analisis = Analisis.objects.get(pk=123)
ejemplo = promover_analisis_a_ejemplo(analisis, origen="chatbot")
```

---

## 7. Buenas prácticas

### Añadir ejemplos

| ✅ Hacer | ❌ No hacer |
|----------|-------------|
| Variar phrasing ("quiero", "necesito", "me gustaría") | Duplicar ejemplos idénticos |
| Incluir entidades reales | Inventar entidades que no existen |
| Balancear clases (~50 por intención) | Tener 500 de una y 5 de otra |
| Usar lenguaje natural del usuario | Usar lenguaje técnico artificial |

### Balanceo de clases

```bash
# Ver distribución
python -c "
from entrenamiento.models import EjemploNLP
from collections import Counter
c = Counter(EjemploNLP.objects.values_list('intencion__nombre', flat=True))
for k, v in c.items():
    print(f'{k}: {v}')
"
```

### Validación cruzada

```bash
# Split manual 80/20 determinístico (ya implementado en generar_nlp)
# Semilla fija en config.cfg: seed = 0
```

---

## 7. Troubleshooting entrenamiento

| Error | Causa | Solución |
|-------|-------|----------|
| `spans not aligned` | Offsets no coinciden con tokens | Revisar `entidades` en CSV |
| `no examples for intent` | Clase sin ejemplos en train/dev | Añadir ejemplos o reducir dev-ratio |
| `CUDA out of memory` | GPU llena | Usar CPU: `python -m spacy train ... --gpu-id -1` |
| Score bajo (<0.85) | Datos insuficientes/ruido | Añadir ejemplos, limpiar ruido, más epochs |
| `model-best` no existe | Entrenamiento no terminó | Ver logs, aumentar `max_steps` |

### Debug rápido

```bash
# Ver ejemplos por intención
python -c "
from entrenamiento.models import EjemploNLP
for e in EjemploNLP.objects.filter(intencion__nombre='compra')[:3]:
    print(f'- {e.texto}')
"

# Ver distribución train/dev
python -c "
import spacy
from spacy.tokens import DocBin
db = DocBin().from_disk('entrenamiento/spacy/train.spacy')
nlp = spacy.blank('es')
cats = {}
for doc in db.get_docs(nlp.vocab):
    for cat, v in doc.cats.items():
        if v == 1.0:
            cats[cat] = cats.get(cat, 0) + 1
print('Train:', cats)
"
```

---

## Referencias

- 📖 [Instrucciones instalación](../instrucciones_instalacion.md)
- 🐳 [Dockerización](../dockerizacion.md)
- 📋 [README principal](../README.md)
- 📚 [spaCy training docs](https://spacy.io/usage/training)
- 🤖 [Ollama Modelfile](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
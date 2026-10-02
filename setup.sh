#!/bin/sh
# One-shot initialization. Runs on every `docker compose up`, but every
# step is idempotent, so after the first run it finishes in seconds.
#
# Env switches:
#   FORCE_RELOAD=1        re-run the cargar_* imports
#   FORCE_TRAIN=1         regenerate the training data and retrain spaCy
#   CARGAR_COMMANDS="a b" explicit list/order of import commands
#                         (default: every command starting with cargar_, alphabetical)
set -e

echo "==> [1/5] Database migrations"
python manage.py migrate --noinput

echo "==> [2/5] Initial data import"
if [ ! -f /data/.data_loaded ] || [ "$FORCE_RELOAD" = "1" ]; then
  python manage.py cargar_datos_iniciales
  touch /data/.data_loaded
else
  echo "    already imported, skipping"
fi

echo "==> [3/5] spaCy training data + config"
SPACY_DIR=entrenamiento/spacy
mkdir -p "$SPACY_DIR"
if [ ! -d "$SPACY_DIR/modelo/model-best" ] || [ "$FORCE_TRAIN" = "1" ]; then
  python manage.py generar_nlp
  if [ ! -f "$SPACY_DIR/config.cfg" ]; then
    python -m spacy init config "$SPACY_DIR/config.cfg" \
      --lang es --pipeline ner,textcat_multilabel --optimize accuracy
  fi

  echo "==> [4/5] spaCy training (can take a while the first time)"
  python -m spacy train "$SPACY_DIR/config.cfg" \
    --output "$SPACY_DIR/modelo" \
    --paths.train "$SPACY_DIR/train.spacy" \
    --paths.dev "$SPACY_DIR/dev.spacy"
else
  echo "    trained model already exists, skipping (FORCE_TRAIN=1 to retrain)"
  echo "==> [4/5] skipped"
fi

echo "==> [5/5] Ollama modelfiles"
python manage.py generar_modelfiles
python manage.py generar_modelfiles --crear

echo "==> Setup finished"
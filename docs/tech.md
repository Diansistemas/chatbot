# spaCy
Biblioteca NLP para Python

- Orientada a objetos
- Modelos preentrenados
- Diseñada para producción

## Componentes
- tagger: Añade etiquetas de uso interno a cada palabra, por token
- morphologizer: Analisis formologico de cada palabra , por token
- trainable_lemmatizer: Devuelve palabras a su forma base para facilitar su tratamiento, por span
- parser: Estructura sintactica base de cada texto, por token
- ner: Reconoce entidades reales, por span
- spancat: Experimental, varias etiquetas por "divisón" del texto, por span
- textcat: Etiqueta del "documento", por chat
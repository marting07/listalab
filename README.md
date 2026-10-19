# ( ListaLab )

**Una lista dentro de otra.** Aplicación de escritorio educativa con **Python y PySide6** para ejercitar estructuras de datos y recursividad: dos funciones recursivas construyen listas multinivel con primitivas inspiradas en Lisp.

![Interfaz de ListaLab con un árbol de listas de tres niveles](docs/listalab.png)

## Ejecutar

Necesitas **Python 3.10 o superior** y un escritorio gráfico. Funciona como aplicación local, sin servidor ni claves de API.

```bash
git clone https://github.com/marting07/listalab.git
cd listalab
python -m venv .venv
```

Activa el entorno:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instala y abre la aplicación:

```bash
python -m pip install -e .
python -m listalab
```

También puedes ejecutarla con el comando `listalab` después de instalarla. En algunos Linux el ejecutable de Python se llama `python3`.

## Qué puedes hacer

- Explorar seis ejemplos: listas de tres niveles, una matriz, categorías, código como datos, listas vacías y una estructura de seis niveles.
- Ejecutar dos generadores recursivos de **1 a 6 niveles**: lineal y ramificado.
- Escribir una expresión Lisp y visualizarla en un árbol interactivo, en una vista desplegable por niveles o como listas de Python.
- Seleccionar cualquier nodo y ver su ruta, como `data[2][1]`.
- Reemplazar nodos, añadir al final, envolver en una nueva lista o eliminar elementos.
- Practicar las primitivas `atom`, `null`, `eq`, `car`, `cdr` y `cons`, y las operaciones recursivas `length`, `reverse` y `flatten`.
- Consultar los casos base y los pasos recursivos en la pestaña **Recursividad**.
- Deshacer y rehacer hasta 50 cambios de datos.
- Abrir y guardar documentos UTF-8 con extensión `.lisp`.

![Vista desplegable con listas y sublistas de categorías](docs/listalab-niveles.png)

## Una prueba rápida

1. Abre **Primeros pasos**. La expresión inicial es `(1 (2 3) (4 (5 6)) "hola")`.
2. Selecciona el nodo `(4 (5 6))`: su ruta es `data[2]`.
3. Elige **flatten** y pulsa **Calcular resultado**: verás `(4 5 6)`.
4. Pulsa **Aplicar al nodo** para sustituir únicamente esa sublista.
5. Usa **Deshacer** para recuperar la estructura anterior.

Para construir otra lista, escribe, por ejemplo:

```lisp
; Una matriz: cada fila es otra lista.
((1 2 3) (4 5 6) (7 8 9))
```

O representa una expresión simbólica:

```lisp
(define (cuadrado x) (* x x))
```

La aplicación representa esa expresión como datos; no ejecuta un intérprete Lisp.

## El ejercicio: dos funciones recursivas

Las dos funciones que **construyen listas en diferentes niveles** están en [listalab/recursive.py](listalab/recursive.py). Se pueden ejecutar desde el selector de la izquierda:

| Función | Resultado con 3 niveles | Paso recursivo |
| --- | --- | --- |
| `crear_lista_lineal(3)` | `(1 (2 (3)))` | Crea una sublista con un nivel menos. |
| `crear_lista_ramificada(3)` | `(1 (2 (4) (5)) (3 (6) (7)))` | Crea dos sublistas, cada una con un nivel menos. |

En ambas, el **caso base** es `niveles == 1`: se construye una lista con un solo átomo mediante `cons(valor, [])`. El **paso recursivo** reduce `niveles` hasta llegar al caso base. No se usa un ciclo para generar los niveles.

![Generador recursivo ramificado con tres niveles](docs/listalab-recursion.png)

```python
def crear_lista_lineal(niveles, valor=1):
    _check_levels(niveles)
    if niveles == 1:
        return cons(valor, [])
    return cons(valor, cons(crear_lista_lineal(niveles - 1, valor + 1), []))


def crear_lista_ramificada(niveles, valor=1):
    _check_levels(niveles)
    if niveles == 1:
        return cons(valor, [])
    return cons(valor, cons(
        crear_lista_ramificada(niveles - 1, valor * 2),
        cons(crear_lista_ramificada(niveles - 1, valor * 2 + 1), [])))
```

`_check_levels` solo verifica que el argumento sea un entero entre 1 y 6. La construcción la hacen las llamadas recursivas y `cons`.

En la versión lineal, las llamadas `crear_lista_lineal(3, 1)` → `(2, 2)` → `(1, 3)` llegan a `(3)`. Al retornar se construyen `(2 (3))` y finalmente `(1 (2 (3)))`. La versión ramificada realiza dos llamadas por cada nivel que no es base: por ejemplo, los valores 2 y 3 son las ramas de la raíz 1.

### Sin librerías ni utilidades para resolver la lógica de listas

**`recursive.py` no tiene importaciones, ciclos, comprensiones ni rebanadas.** No usa `deepcopy`, `len`, `sum`, `max`, `map`, `filter`, `reversed`, `append`, `extend`, `pop` o `copy`. Además de los dos generadores, implementa recursivamente la copia, concatenación, inversión, aplanado, conteo, acceso por rutas, edición y manejo del historial.

Las primitivas contienen las operaciones elementales necesarias para representar listas en Python: pruebas de tipo, comparación, acceso por índice y la construcción `[cabeza] + cola` dentro de `cons`. `cdr` construye la cola recursivamente por índices, sin usar `lista[1:]`. Las demás funciones trabajan con cabeza y cola, como en un ejercicio de Lisp.

PySide6 se utiliza para la interfaz. El lector y el guardado usan la biblioteca estándar para validar y codificar **texto**, no para resolver los algoritmos de listas. Esas tareas están fuera del núcleo didáctico.

### Primitivas y operaciones atómicas

| Operación | Ejemplo | Resultado |
| --- | --- | --- |
| `atom` | `atom(7)` / `atom((7))` | `#t` / `#f` |
| `null` | `null(())` / `null(nil)` / `null(0)` | `#t` / `#t` / `#f` |
| `eq` | `eq(7, 7)` / `eq(7, "7")` | `#t` / `#f` |
| `car` | `car((a b c))` | `a` |
| `cdr` | `cdr((a b c))` | `(b c)` |
| `cons` | `cons(a, (b c))` | `(a b c)` |

`eq` acepta dos átomos y compara su valor y su tipo; una cadena y un símbolo con el mismo texto son diferentes. Rechaza listas. Los resultados booleanos se muestran como `#t` y `#f`. Para probar `eq` en la app, selecciona un átomo y escribe el segundo en el campo de argumento.

`length` combina el caso base `null(lista) → 0` con el paso `1 + length(cdr(lista))`. El valor de `length` cuenta solo los elementos del nivel seleccionado, sin contar dentro de las sublistas.

## Las listas son la estructura principal

El documento de trabajo es una **`list` de Python que contiene átomos y otras `list`**, sin un árbol de objetos como almacenamiento alternativo:

```python
data = [1, [2, 3], [4, [5, 6]], "hola"]
data[2][1]  # [5, 6]
```

Las rutas son listas de índices. El catálogo de ejemplos también es una lista de listas, con filas `[título, descripción, datos]`. El historial guarda una lista de instantáneas de listas. Los elementos gráficos de Qt se reconstruyen a partir del documento cada vez que cambian los datos.

La recursión se usa para construir, recorrer, serializar, contar y dibujar las sublistas. El lector construye sus listas con dos funciones mutuamente recursivas, `expression` y `sequence`; los dos generadores anteriores crean ejemplos sin leer texto. Las operaciones de la aplicación devuelven copias hechas con `copy_value`, de modo que un resultado o un cambio no altere accidentalmente los ejemplos o el historial. Las primitivas por sí mismas conservan referencias a elementos, como bloques elementales; la aplicación copia al editar y almacenar.

### Operaciones

Para la lista `(1 (2 3) 4)`:

| Operación | Resultado | Comportamiento |
| --- | --- | --- |
| `car` | `1` | Primer elemento, que puede ser un átomo o una sublista. |
| `cdr` | `((2 3) 4)` | Resto de la lista. |
| `cons`, argumento `(a b)` | `((a b) 1 (2 3) 4)` | Inserta un elemento al inicio, conservando su anidación. |
| `reverse` | `(4 (2 3) 1)` | Invierte el nivel seleccionado. |
| `flatten` | `(1 2 3 4)` | Reúne los átomos de todos los niveles; omite listas vacías. |
| `length` | `3` | Cuenta los elementos del nivel seleccionado mediante recursión. |

La raíz siempre debe ser una lista. Los resultados atómicos, incluidos los de los predicados y de `length`, se pueden consultar; solo se pueden aplicar si el nodo seleccionado no es la raíz. `car` y `cdr` sobre `()` devuelven `()`.

### Sintaxis admitida y diferencias con Lisp

- Paréntesis para listas; espacios entre átomos.
- Enteros, decimales finitos y notación exponencial.
- Símbolos sin comillas, como `cuadrado`, y cadenas con comillas dobles, como `"hola mundo"`.
- Las cadenas usan escapes JSON: `\n`, `\"`, `\\`, etc.
- Booleanos `#t` y `#f`; `nil` se convierte en `None`.
- Comentarios desde `;` hasta el final de la línea y una comilla inicial opcional: `'(1 (2 3))`.
- Se admite una expresión por documento; no hay evaluación, macros, pares punteados ni lectura de código Python.

Es una herramienta inspirada en Lisp, con listas dinámicas de Python en lugar de celdas cons enlazadas. Para hacer visibles los distintos tipos, **`nil` y `()` se representan por separado**; en Common Lisp designan el mismo valor. Aquí `atom(())` devuelve `#f` y `atom(nil)` devuelve `#t`, mientras que `null` reconoce ambos como vacíos. `eq` usa igualdad de valor y tipo para átomos, no la identidad de objetos de Common Lisp. La sintaxis booleana sigue la convención de Scheme. `flatten` es una operación educativa adicional.

`Symbol` es una subclase de `str` que permite conservar la diferencia entre `hola` y `"hola"` al guardar. En la pestaña Python ambos se muestran con comillas por su representación de cadena; las vistas Lisp conservan la distinción.

## Controles y archivos

| Acción | Control |
| --- | --- |
| Visualizar el editor | `Ctrl+Enter` |
| Abrir / guardar | `Ctrl+O` / `Ctrl+S` |
| Deshacer / rehacer datos | Botones o `Ctrl+Alt+Z` / `Ctrl+Alt+Y` |
| Deshacer texto del editor | `Ctrl+Z` |
| Acercar / alejar el árbol | Botones o `Ctrl` + rueda |
| Desplazar el árbol | Arrastrar o barras de desplazamiento |
| Guía rápida | `F1` |

Visualiza los cambios del editor antes de editar nodos, abrir ejemplos o guardar. Los errores conservan el último documento válido. Los archivos de [examples/](examples/) pueden abrirse directamente en la aplicación. Guardar conserva símbolos y tipos en notación Lisp, sin los comentarios o el formato original. El historial es temporal y no hay guardado automático.

La métrica **niveles** cuenta únicamente la profundidad de listas, incluida la raíz. Los colores del árbol indican la profundidad visual de cada nodo. Para mantener una interfaz manejable se admiten hasta **12 niveles de listas, 500 nodos y 32 000 caracteres** por documento. El generador ofrece hasta seis niveles; el editor admite los doce.

## Desarrollo y verificación

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Las pruebas de interfaz usan widgets y eventos Qt reales con `QT_QPA_PLATFORM=offscreen`, sin necesitar una pantalla. Verifican selección por clic en el diagrama, edición, ambos generadores, operaciones atómicas, historial, lectura/escritura, ejemplos y entradas inválidas. Las pruebas del núcleo verifican los casos base y recursivos, la independencia de las ramas, el límite de 500 nodos y la ausencia de importaciones, ciclos, comprensiones, rebanadas y utilidades prohibidas. El flujo de GitHub Actions está configurado para ejecutarlas en Linux y Windows con Python 3.10 y 3.12.

En un Linux mínimo pueden hacer falta las bibliotecas del sistema de Qt. En Ubuntu/Debian: `sudo apt-get install libegl1 libopengl0 libxcb-cursor0`. El modo `offscreen` sirve para pruebas; para usar la app necesitas una sesión gráfica.

```text
listalab/
  recursive.py   Primitivas, dos generadores y algoritmos recursivos; sin imports
  model.py       Lector, validación y documento; delega la lógica a recursive.py
  diagram.py     Árbol interactivo derivado de las listas
  app.py         Ventana, acciones y archivos
  style.py       Apariencia de la interfaz
examples/        Documentos Lisp listos para abrir
tests/           Pruebas del modelo y la interfaz
docs/            Capturas reales de la app
```

Licencia [MIT](LICENSE).

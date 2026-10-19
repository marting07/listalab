"""Núcleo didáctico sin imports, ciclos, comprensiones ni utilidades de listas.

Solo las primitivas car/cdr/cons conocen la representación de la lista Python.
Las demás funciones combinan esas primitivas, pruebas atómicas y recursión.
cons usa [cabeza] + cola como construcción elemental, sin modificar sus entradas.
"""


def atom(value):
    """Un átomo es un valor que no es una lista; () no es un átomo aquí."""
    return not isinstance(value, list)


def null(value):
    """Reconoce tanto la lista vacía como nil (None en el lector)."""
    return value is None or value == []


def eq(left, right):
    """Igualdad de átomos del mismo tipo; no compara estructuras de listas."""
    if not atom(left) or not atom(right):
        raise ValueError("eq compara dos átomos. Para listas, selecciona sus elementos.")
    return type(left) is type(right) and left == right


def car(items):
    if atom(items):
        raise ValueError("car necesita una lista.")
    return [] if null(items) else items[0]


def cons(head, tail):
    if atom(tail):
        raise ValueError("La cola de cons debe ser una lista.")
    return [head] + tail


def cdr(items):
    """Construye la cola recursivamente, sin rebanadas ni métodos de listas."""
    if atom(items):
        raise ValueError("cdr necesita una lista.")
    return _tail(items, 1)


def _tail(items, index):
    # El acceso por índice solo aparece en las primitivas de representación.
    try:
        head = items[index]
    except IndexError:
        return []
    return cons(head, _tail(items, index + 1))


def copy_value(value):
    """Copia profunda: caso átomo, caso vacío y caso cabeza/cola."""
    if atom(value):
        return value
    if null(value):
        return []
    return cons(copy_value(car(value)), copy_value(cdr(value)))


def concat(left, right):
    if atom(left) or atom(right):
        raise ValueError("concat necesita dos listas.")
    if null(left):
        return copy_value(right)
    return cons(copy_value(car(left)), concat(cdr(left), right))


def length(items):
    """Cuenta el nivel seleccionado sin len, sum o ciclos."""
    if atom(items):
        raise ValueError("length necesita una lista.")
    if null(items):
        return 0
    return 1 + length(cdr(items))


def reverse(items):
    if atom(items):
        raise ValueError("reverse necesita una lista.")
    return _reverse(items, [])


def _reverse(items, result):
    if null(items):
        return result
    return _reverse(cdr(items), cons(copy_value(car(items)), result))


def flatten(items):
    if atom(items):
        raise ValueError("flatten necesita una lista.")
    if null(items):
        return []
    head = car(items)
    if atom(head):
        return cons(head, flatten(cdr(items)))
    return concat(flatten(head), flatten(cdr(items)))


def stats(value):
    """Devuelve [listas, átomos, niveles] sin sum, max o comprensiones."""
    if atom(value):
        return [0, 1, 0]
    totals = _stats_items(value)
    return [1 + car(totals), car(cdr(totals)), 1 + car(cdr(cdr(totals)))]


def _stats_items(items):
    if null(items):
        return [0, 0, 0]
    head = stats(car(items))
    tail = _stats_items(cdr(items))
    head_depth = car(cdr(cdr(head)))
    tail_depth = car(cdr(cdr(tail)))
    return [car(head) + car(tail), car(cdr(head)) + car(cdr(tail)),
            head_depth if head_depth > tail_depth else tail_depth]


def _check_levels(levels):
    if type(levels) is not int or levels < 1 or levels > 6:
        raise ValueError("El generador admite entre 1 y 6 niveles.")


def crear_lista_lineal(niveles, valor=1):
    """Base: un nivel. Paso: un átomo y una sublista de niveles - 1."""
    _check_levels(niveles)
    if niveles == 1:
        return cons(valor, [])
    return cons(valor, cons(crear_lista_lineal(niveles - 1, valor + 1), []))


def crear_lista_ramificada(niveles, valor=1):
    """Base: un nivel. Paso: un átomo y dos sublistas de niveles - 1."""
    _check_levels(niveles)
    if niveles == 1:
        return cons(valor, [])
    return cons(valor, cons(
        crear_lista_ramificada(niveles - 1, valor * 2),
        cons(crear_lista_ramificada(niveles - 1, valor * 2 + 1), [])))


def _item(items, index):
    if atom(items) or null(items):
        raise ValueError("La ruta seleccionada ya no existe.")
    if index == 0:
        return car(items)
    return _item(cdr(items), index - 1)


def _check_index(index):
    if type(index) is not int or index < 0:
        raise ValueError("La ruta seleccionada ya no existe.")


def at(data, path):
    if null(path):
        return data
    index = car(path)
    _check_index(index)
    return at(_item(data, index), cdr(path))


def replace_path(data, path, value):
    if null(path):
        return copy_value(value)
    index = car(path)
    _check_index(index)
    return _replace_item(data, index, cdr(path), value)


def _replace_item(items, index, remaining_path, value):
    if atom(items) or null(items):
        raise ValueError("La ruta seleccionada ya no existe.")
    if index == 0:
        return cons(replace_path(car(items), remaining_path, value), copy_value(cdr(items)))
    return cons(copy_value(car(items)), _replace_item(cdr(items), index - 1, remaining_path, value))


def remove_path(data, path):
    if null(path):
        raise ValueError("La raíz no se elimina. Puedes sustituirla por ().")
    index = car(path)
    _check_index(index)
    return _remove_item(data, index, cdr(path))


def _remove_item(items, index, remaining_path):
    if atom(items) or null(items):
        raise ValueError("La ruta seleccionada ya no existe.")
    if index == 0:
        if null(remaining_path):
            return copy_value(cdr(items))
        return cons(remove_path(car(items), remaining_path), copy_value(cdr(items)))
    return cons(copy_value(car(items)), _remove_item(cdr(items), index - 1, remaining_path))


def take(items, count):
    """Prefijo recursivo para limitar el historial de instantáneas."""
    if count <= 0 or null(items):
        return []
    return cons(car(items), take(cdr(items), count - 1))

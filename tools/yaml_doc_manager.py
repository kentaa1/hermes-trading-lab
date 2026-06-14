#!/usr/bin/env python3
"""yaml_doc_manager.py — Manejo de YAML docstrings en archivos Python.

Extrae y actualiza bloques YAML incrustados en docstrings de funciones.
"""

import re
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def to_native(obj: Any) -> Any:
    """Convierte tipos numpy a tipos nativos de Python recursivamente.

    Args:
        obj: Objeto a convertir (puede ser dict, list, o escalar numpy).

    Returns:
        Objeto con tipos nativos de Python.
    """
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_native(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return to_native(obj.tolist())
    return obj


def _find_docstring_yaml_block(source: str) -> tuple[int, int, int, str] | None:
    """Busca un bloque YAML dentro de un docstring en el source.

    Args:
        source: Contenido del archivo Python.

    Returns:
        Tupla (start, end, indent, yaml_text) donde:
        - start: indice de inicio de '---' en source
        - end: indice de fin de '---' (inmediatamente despues del ultimo '---')
        - indent: espacios de indentacion del bloque YAML
        - yaml_text: texto YAML sin indentacion
        O None si no encuentra.
    """
    # Buscar triple-comilla docstrings
    pattern = r'"""(.+?)"""'
    for match in re.finditer(pattern, source, re.DOTALL):
        inner = match.group(1)
        lines = inner.split("\n")

        open_idx = -1
        close_idx = -1
        indent = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "---":
                if open_idx == -1:
                    open_idx = i
                    indent = len(line) - len(line.lstrip())
                else:
                    close_idx = i
                    break

        if open_idx != -1 and close_idx != -1:
            yaml_lines = []
            for line in lines[open_idx + 1:close_idx]:
                stripped = line.strip()
                if not stripped:
                    continue
                if len(line) > indent:
                    yaml_lines.append(line[indent:])
                else:
                    yaml_lines.append(line)
            yaml_text = "\n".join(yaml_lines)

            # Calcular start/end en source
            doc_start = match.start(1)
            lines_before_open = lines[:open_idx]
            chars_before_open = sum(len(l) + 1 for l in lines_before_open)  # +1 por \n
            start = doc_start + chars_before_open

            lines_before_close = lines[:close_idx + 1]
            chars_before_close = sum(len(l) + 1 for l in lines_before_close)
            # Cerrar despues del ultimo '---' (incluye el final \n si existe)
            end = doc_start + chars_before_close

            return (start, end, indent, yaml_text)

    return None


def extract_yaml_docstring(file_path: Path) -> dict:
    """Lee un archivo Python y extrae el bloque YAML dentro del docstring de una funcion.

    Busca el primer docstring de funcion que contenga un bloque YAML delimitado
    por '---'. Maneja indentacion variable (0, 4, 8 espacios).

    Args:
        file_path: Ruta al archivo Python.

    Returns:
        Dict con el contenido YAML parseado. Dict vacio si no encuentra YAML.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el YAML no puede ser parseado.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    source = path.read_text(encoding="utf-8")
    block = _find_docstring_yaml_block(source)

    if block is None:
        return {}

    try:
        result = yaml.safe_load(block[3])
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parseando YAML en {file_path}: {e}")


def update_yaml_docstring(file_path: str, data: dict) -> None:
    """Actualiza las keys del YAML docstring en un archivo Python.

    Lee el archivo, extrae el YAML existente, actualiza solo las keys
    proporcionadas, y escribe el YAML actualizado manteniendo el formato original.

    Args:
        file_path: Ruta al archivo Python (string por compatibilidad).
        data: Dict con las keys a actualizar/agregar.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si no encuentra YAML docstring en el archivo.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    source = path.read_text(encoding="utf-8")
    block = _find_docstring_yaml_block(source)

    if block is None:
        raise ValueError(f"No se encontro bloque YAML docstring en {file_path}")

    start, end, indent, old_yaml_text = block
    old_data = yaml.safe_load(old_yaml_text) or {}
    old_data.update(to_native(data))

    new_yaml_str = yaml.safe_dump(old_data, sort_keys=False, allow_unicode=True).strip()

    # Reconstruir el bloque YAML manteniendo la indentacion original
    indent_str = " " * indent
    indented = "\n".join(indent_str + line for line in new_yaml_str.split("\n"))
    new_block = indent_str + "---\n" + indented + "\n" + indent_str + "---"

    updated = source[:start] + new_block + source[end:]
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    import tempfile

    example = '''def my_function(param1: int) -> dict:
    """Computes something.

    ---
    author: test
    version: 1
    tags:
      - demo
      - example
    ---

    Args:
        param1: First parameter.
    """
    return {"param1": param1}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = Path(tmpdir) / "example.py"
        tmpfile.write_text(example)
        print("=== YAML extraido ===")
        result = extract_yaml_docstring(tmpfile)
        print(result)
        assert result == {"author": "test", "version": 1, "tags": ["demo", "example"]}, f"Unexpected: {result}"
        print("OK")
        print()

        update_yaml_docstring(str(tmpfile), {"version": 2, "new_key": "value"})
        print("=== Archivo actualizado ===")
        content = tmpfile.read_text()
        print(content)
        print()

        print("=== YAML re-extraido ===")
        result2 = extract_yaml_docstring(tmpfile)
        print(result2)
        assert result2.get("version") == 2, f"version not updated: {result2}"
        assert result2.get("new_key") == "value", f"new_key missing: {result2}"
        assert result2.get("author") == "test", f"author lost: {result2}"
        assert result2.get("tags") == ["demo", "example"], f"tags lost: {result2}"
        print("OK")
        print()

        print("=== Tests pasaron ===")

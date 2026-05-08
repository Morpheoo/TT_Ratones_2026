# Sistema de Gestión de Tratamientos - Documentación

## Descripción

El sistema de tratamientos permite gestionar de forma centralizada los tratamientos experimentales disponibles en el Sistema EPM, con diferentes niveles de acceso según el rol del usuario.

## Arquitectura

### Base de Datos

Nueva tabla `treatments`:
```sql
CREATE TABLE treatments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Módulo Python

Archivo: `src/treatments.py`

Funciones disponibles:
- `initialize_treatments_table()`: Crea la tabla e inserta tratamientos por defecto
- `get_all_treatments()`: Obtiene todos los tratamientos activos
- `add_treatment(name, description, created_by)`: Añade un nuevo tratamiento
- `delete_treatment(treatment_id)`: Elimina o desactiva un tratamiento
- `get_treatment_by_name(name)`: Busca un tratamiento específico

## Niveles de Acceso por Rol

### Estudiante
- **Ver**: Lista completa de tratamientos
- **Seleccionar**: Puede elegir cualquier tratamiento de la lista
- **Restricciones**: No puede añadir ni eliminar tratamientos

### Investigador
- **Ver**: Lista completa de tratamientos
- **Seleccionar**: Puede elegir cualquier tratamiento de la lista
- **Añadir**: Puede crear nuevos tratamientos con nombre y descripción
- **Restricciones**: No puede eliminar tratamientos

### Administrador
- **Ver**: Lista completa de tratamientos
- **Seleccionar**: Puede elegir cualquier tratamiento de la lista
- **Añadir**: Puede crear nuevos tratamientos con nombre y descripción
- **Eliminar**: Puede eliminar tratamientos (se desactivan si están en uso)

## Interfaz de Usuario

### Página: Ingesta de Video

**Todos los roles:**
- Selectbox desplegable con todos los tratamientos disponibles

**Investigadores y Administradores:**
- Expander "Añadir Nuevo Tratamiento"
  - Campo de texto para nombre
  - Área de texto para descripción
  - Botón "Añadir Tratamiento"

**Solo Administradores:**
- Expander "Gestionar Tratamientos (Admin)"
  - Selectbox para elegir tratamiento a eliminar
  - Botón "Eliminar"
  - Advertencia sobre desactivación si está en uso

## Tratamientos por Defecto

Al inicializar el sistema, se crean automáticamente:
1. Control
2. Diazepam 5mg
3. Diazepam 10mg
4. Cafeína 50mg
5. Estrés por restricción

## Inicialización

Ejecutar una vez después de actualizar el código:

```bash
python init_treatments.py
```

Esto creará la tabla y cargará los tratamientos por defecto.

## Eliminación Segura

Cuando un administrador intenta eliminar un tratamiento:
- Si NO está en uso en ningún experimento: Se elimina completamente
- Si SÍ está en uso: Se marca como `is_active = FALSE` (desactivado)
- Los tratamientos desactivados no aparecen en las listas pero mantienen integridad referencial

## Flujo de Trabajo

1. Usuario carga la página de Ingesta de Video
2. Sistema inicializa tabla de tratamientos (solo primera vez)
3. Sistema carga lista de tratamientos activos
4. Usuario selecciona tratamiento del dropdown
5. (Opcional) Investigador/Admin añade nuevo tratamiento
6. (Opcional) Admin elimina tratamiento no deseado
7. Usuario continúa con el flujo normal de ingesta

## Ventajas del Sistema

- **Consistencia**: Todos usan los mismos nombres de tratamientos
- **Control**: Administradores gestionan el catálogo
- **Flexibilidad**: Investigadores pueden añadir tratamientos nuevos
- **Seguridad**: Estudiantes no pueden modificar el catálogo
- **Trazabilidad**: Se registra quién creó cada tratamiento
- **Integridad**: No se pierden datos al eliminar tratamientos en uso

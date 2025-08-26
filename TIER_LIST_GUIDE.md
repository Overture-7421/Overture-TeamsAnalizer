# 🎯 Guía Completa del Sistema de Tier List

## Descripción General

El Sistema de Tier List permite exportar los resultados del Honor Roll en un formato específico compatible con aplicaciones móviles Dart/Flutter. Incluye soporte completo para imágenes de robots y categorización automática por niveles de rendimiento.

## 🏆 Categorías del Tier List

### Equipos Calificados (Orden por Honor Roll Score)

#### 1st Pick - Primera Selección
- **Criterio**: 33% superior de equipos calificados
- **Descripción**: Los mejores equipos con mayor Honor Roll Score
- **Uso recomendado**: Primera opción para capitanes de alianza

#### 2nd Pick - Segunda Selección
- **Criterio**: 33% medio de equipos calificados
- **Descripción**: Equipos sólidos con buen rendimiento
- **Uso recomendado**: Buenas opciones para completar alianzas

#### 3rd Pick - Tercera Selección
- **Criterio**: 33% inferior de equipos calificados (pero aún calificados)
- **Descripción**: Equipos que cumplen estándares mínimos
- **Uso recomendado**: Opciones de respaldo

### Categorías Especiales

#### Ojito
- **Criterio**: Categoría especial (vacía por defecto)
- **Descripción**: Para equipos que requieren atención especial
- **Uso**: Marcado manual o criterios personalizados

#### - (Dash) - Reprobados
- **Criterio**: Equipos descalificados del Honor Roll que NO son defensivos
- **Descripción**: Equipos que no cumplen estándares mínimos
- **Exclusión**: No incluye equipos defensivos

#### Defense Pick - Selección Defensiva
- **Criterio**: TODOS los equipos con defense_rate > 0.3
- **Descripción**: Equipos especializados en juego defensivo
- **Incluye**: Tanto calificados como descalificados si son defensivos

#### Unassigned - Sin Asignar
- **Criterio**: Categoría vacía por defecto
- **Descripción**: Para equipos pendientes de clasificación
- **Uso**: Organización adicional según necesidades

## 🖼️ Sistema de Imágenes

### Imágenes por Defecto

Las imágenes por defecto se generan automáticamente con:
- **Diseño**: Robot estilizado con colores corporativos
- **Contenido**: Número del equipo visible
- **Formato**: PNG de 150x150 píxeles
- **Codificación**: Base64 para compatibilidad móvil

#### Elementos Visuales
- Cuerpo del robot en azul corporativo
- Cabeza con "ojos" LED blancos
- Brazos articulados a los lados
- Número del equipo centrado en el cuerpo
- Fondo oscuro profesional

### Imágenes Personalizadas

#### Estructura de Carpeta
```
robot_images/
├── 1234.png
├── 5678.jpg
├── 9012.jpeg
├── 3456.gif
└── 7890.bmp
```

#### Requisitos
- **Nomenclatura**: Nombre del archivo = número del equipo
- **Formatos soportados**: PNG, JPG, JPEG, GIF, BMP
- **Tamaño recomendado**: 150x150 píxeles (se redimensiona automáticamente)
- **Codificación**: Se convierte automáticamente a base64

#### Proceso de Carga
1. Se busca imagen con nombre exacto del equipo
2. Si se encuentra, se carga y redimensiona
3. Si no se encuentra, se genera imagen por defecto
4. Se codifica en base64 para inclusión en tier list

## 📝 Formato de Archivo Tier List

### Estructura General
```
Tier: [Nombre de Categoría]
  Image: [base64_encoded_image]
    Title: Team [Número] (Honor Roll Score: [Score])
    Text: [JSON con estadísticas completas]
    DriverSkills: [Offensive/Defensive]
    ImageList:

```

### Campos de Información

#### Title
- **Formato**: `Team {número} (Honor Roll Score: {score})`
- **Ejemplo**: `Team 1234 (Honor Roll Score: 85.50)`

#### Text (JSON)
Incluye estadísticas completas del equipo:
```json
{
  "honor_score": 85.5,
  "final_points": 120,
  "overall_avg": 85.2,
  "robot_valuation": 90.1,
  "defense_rate": 0.1,
  "died_rate": 0.05,
  "matches_played": 12
}
```

#### DriverSkills
- **Offensive**: Equipos con defense_rate ≤ 0.3
- **Defensive**: Equipos con defense_rate > 0.3

## 🚀 Proceso de Exportación

### Paso a Paso

1. **Ejecutar Honor Roll**
   - Cargar datos CSV
   - Configurar parámetros del Honor Roll
   - Ejecutar análisis completo

2. **Preparar Imágenes (Opcional)**
   - Crear carpeta con imágenes de robots
   - Nombrar archivos con número de equipo
   - Verificar formatos soportados

3. **Exportar Tier List**
   - Hacer clic en "Export to Tier List"
   - Seleccionar si usar carpeta de imágenes
   - Elegir ubicación del archivo de salida

4. **Verificar Resultado**
   - Revisar archivo generado
   - Confirmar que incluye imágenes
   - Validar formato para aplicación destino

### Mensajes del Sistema

#### Selección de Imágenes
- Pregunta si desea usar carpeta de imágenes
- Explica nomenclatura requerida
- Ofrece usar imágenes por defecto

#### Confirmaciones
- Carpeta seleccionada exitosamente
- Generación de imágenes por defecto
- Exportación completada

## 🔧 Compatibilidad Técnica

### Aplicaciones Dart/Flutter

El formato está diseñado específicamente para:
- Parser de tier lists en Dart
- Aplicaciones móviles Flutter
- Sistemas de carga de imágenes base64

### Estructura Compatible
```dart
class TierListItem {
  String image;      // base64 string
  String title;      // team info
  Map text;          // statistics JSON
  String driverSkills; // offensive/defensive
  List imageList;    // additional images
}
```

## 📊 Ejemplos y Casos de Uso

### Competencia Típica
- **40 equipos totales**
- **25 equipos calificados** → 8 en cada tier (1st, 2nd, 3rd)
- **15 equipos descalificados** → distribuidos entre "-" y "Defense Pick"
- **6 equipos defensivos** → todos en "Defense Pick"

### Escenario de Selección
1. **Capitán**: Revisa 1st Pick para primera selección
2. **Segunda ronda**: Considera 2nd Pick para balance
3. **Estrategia defensiva**: Evalúa Defense Pick
4. **Último recurso**: 3rd Pick para completar alianza

## 🛠️ Mantenimiento y Troubleshooting

### Problemas Comunes

#### Imágenes No Cargan
- Verificar nomenclatura exacta (número.extensión)
- Confirmar formatos soportados
- Revisar permisos de carpeta

#### Archivo Tier List Vacío
- Ejecutar Honor Roll primero
- Verificar que hay equipos calificados
- Revisar logs de consola para errores

#### Errores de Codificación
- Problema con caracteres especiales en nombres
- Verificar encoding UTF-8 en archivos
- Revisar estadísticas JSON válido

### Logs de Depuración
El sistema genera logs detallados:
- Número de equipos encontrados
- Equipos defensivos identificados
- Errores de carga de imágenes
- Estadísticas de exportación

## 📈 Mejores Prácticas

### Preparación de Datos
1. Ejecutar análisis completo antes de exportar
2. Verificar configuración de Honor Roll
3. Revisar equipos defensivos identificados

### Gestión de Imágenes
1. Mantener carpeta organizada por competencia
2. Usar nombres de archivo consistentes
3. Optimizar tamaño de imágenes para rendimiento

### Validación de Resultados
1. Revisar distribución de equipos por tier
2. Verificar que equipos defensivos estén bien clasificados
3. Confirmar estadísticas JSON válidas

---

## 📞 Soporte Adicional

Para dudas específicas sobre el Sistema de Tier List:
1. Revisar archivos de ejemplo incluidos
2. Probar con datos de test
3. Verificar logs de consola para errores específicos
4. Consultar documentación de la aplicación destino Dart/Flutter

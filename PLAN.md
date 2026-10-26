# Plan de correccion

## Alcance y contrato observado

Se seleccionan H-AUTH-01 a H-AUTH-07 porque todos aparecen como `Pendiente` en `HALLAZGOS.md`; no se proporciono un subconjunto. H-AUTH-07 se incluye como verificacion SCA, no como confirmacion de un CVE ni como aprobacion de una actualizacion.

No existe `docs/ENDPOINTS.md`. Se toma como contrato observado `POST /auth/login`, con JSON que contiene `username` y `password` (tambien se acepta el campo `client`), respuestas 400 para request/campos obligatorios ausentes, 401 para credenciales sin coincidencia, 200 con `token`, `expiresIn` y `user` (username, displayName y role), y 500 ante excepciones no controladas. El codigo agrega `debug` a la respuesta exitosa. La unica prueba existente caracteriza el 200, `user.username` y presencia del token. Se propone conservar ruta, codigos de estado y forma de la respuesta exitosa; los errores internos deben volverse genericos sin cambiar el estado 500 ni exponer excepciones. No se afirma que consumidores externos hayan sido verificados.

## H-AUTH-01 - Credenciales concatenadas en SQL

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-01. `LegacyDatabase.findByCredentials` concatena username y password en el SQL y lo ejecuta con `Statement` (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:31-35`).
- **Problema:** los valores de entrada pueden alterar la consulta en vez de compararse exclusivamente como datos.
- **Cambio propuesto:** sustituir la consulta por `PreparedStatement` y parametros enlazados. Mantener el mismo criterio de busqueda y retornar el mismo `UserRecord` o `null`, sin modificar la respuesta HTTP del login.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` y, si conviene aislar el repositorio, una prueba nueva bajo `auth/src/test/java/com/bcp/workshop/auth/`.
- **Caracterizacion antes del cambio:** ampliar la prueba del endpoint para registrar el login ficticio valido y el 401 con credenciales incorrectas. Agregar un caso con comilla simple en username y comprobar que no autentica (401); no usar un servicio remoto ni payloads de explotacion. No ejecutar estas pruebas antes de implementarlas.
- **Ejecuciones (auth, H-AUTH-01, 2026-10-26):** antes del cambio, `mvn test` desde `auth/`: 3 pruebas, 0 fallos; la comilla recibio 401 y genero `SQLITE_ERROR`/stack trace en el servidor. Despues de parametrizar, `mvn test`: 3 pruebas, 0 fallos y sin error SQL. Tras explicitar `PreparedStatement` y ajustar indentacion, `mvn test`: 3 pruebas, 0 fallos.

## H-AUTH-02 - Contrasenas en texto plano

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-02. El esquema y las filas semilla almacenan contrasenas legibles, y la consulta las compara directamente (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:22-24,32`).
- **Problema:** una lectura o copia de la base revela credenciales reutilizables; una migracion incompleta podria bloquear usuarios existentes.
- **Cambio propuesto:** usar hash lento con salt, conforme a `docs/GOOD_PRACTICES.md`. Preferir una implementacion del JDK (`PBKDF2WithHmacSHA256`, `SecureRandom`) para evitar una dependencia adicional. Actualizar de forma transaccional las contrasenas existentes en la base local al formato versionado de hash y hacer que el login verifique el hash. No registrar contrasenas ni hashes. Definir constantes con nombre para parametros del algoritmo.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`, una clase de servicio/utilidad de hash nueva bajo `auth/src/main/java/com/bcp/workshop/auth/`, y pruebas nuevas bajo `auth/src/test/java/com/bcp/workshop/auth/`.
- **Caracterizacion antes del cambio:** en una base SQLite temporal, comprobar que los usuarios ficticios actuales pueden iniciar sesion y que una contrasena incorrecta produce 401; guardar tambien el comportamiento de usuarios preexistentes antes de migrarlos. Tras el cambio, verificar migracion repetible, hash distinto del texto original y validacion positiva/negativa. No se ejecutaron estas pruebas.
- **Ejecuciones (auth, H-AUTH-02, 2026-10-26):** antes del cambio, `mvn test` desde `auth/` con `AUTH_DB_URL` apuntando a una SQLite temporal: 4 pruebas, 0 fallos; la prueba nueva confirmó que la contraseña legada seguía almacenada literalmente tras inicializar. Después del cambio, `mvn test`: 5 pruebas, 0 fallos; verificó hash con salt único, validación positiva/negativa, migración repetible y login del usuario migrado. `mvn verify`: 5 pruebas, 0 fallos, BUILD SUCCESS. JaCoCo (`auth/target/site/jacoco/jacoco.csv`): `PasswordHasher` 34/36 líneas (94,4%); `LegacyDatabase` 49/55 (89,1%).
- **Revision local (auth, H-AUTH-02):** se reabre como `Pendiente`: si la migracion falla, `initialize()` revierte, imprime la excepcion y permite que el servicio siga arrancando; las filas legadas pueden permanecer en texto plano. Pendiente tambien caracterizar y mitigar la diferencia temporal entre usuario inexistente y contraseña incorrecta en `LegacyDatabase.findByCredentials`.

## H-AUTH-03 - Token Base64 sin firma

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-03. `LegacyTokenUtil` agrega username, role, expiracion y secreto fijo, y solo codifica el contenido con Base64 (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,13-15`).
- **Problema:** Base64 no autentica ni protege la integridad del contenido. Cambiar la representacion interna tambien puede afectar a consumidores que no estan dentro del alcance revisado.
- **Cambio propuesto:** emitir un token firmado con expiracion y claims explicitos usando una biblioteca JWT compatible y mantenida, preferiblemente integrada con Quarkus, en vez de implementar criptografia/serializacion propia. Mantener los campos existentes de la respuesta de login y `expiresIn`; no cambiar la ruta ni los codigos de estado. Externalizar la clave de firma como parte de H-AUTH-05. Antes de implementar, confirmar el formato esperado por consumidores sin leer ni cambiar otros componentes en este paso.
- **Archivos a tocar:** `auth/pom.xml` solo si se justifica la biblioteca, `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o un emisor nuevo, `auth/src/main/resources/application.properties` y pruebas nuevas bajo `auth/src/test/java/com/bcp/workshop/auth/`.
- **Caracterizacion antes del cambio:** ampliar `AuthResourceTest` para capturar status 200, nombres de campos, usuario y `expiresIn` en la respuesta exitosa. No fijar el contenido Base64 actual como contrato. Luego probar firma verificable, claims esperados, expiracion y rechazo de token alterado con la biblioteca elegida.

## H-AUTH-04 - Detalles de excepcion en HTTP 500

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-04. El `catch` devuelve `error.getMessage()` y `error.getClass().getName()` (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:52-58`).
- **Problema:** los clientes reciben detalles internos que pueden revelar clases, mensajes o estado del servidor.
- **Cambio propuesto:** responder con mensaje generico y no incluir informacion de la excepcion. Mantener el status 500 y las claves observadas `message` y `exception` con valores constantes no sensibles, si conservar la forma JSON resulta necesario para compatibilidad. Registrar el detalle solo en el log del servidor, sin credenciales.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java` o un mapper de excepciones nuevo en `auth/src/main/java/com/bcp/workshop/auth/`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Caracterizacion antes del cambio:** provocar una excepcion controlada mediante un doble de prueba de la dependencia, y registrar que el endpoint responde 500 con las claves actuales. No fijar ni validar el texto interno; la prueba posterior debe comprobar que la respuesta es generica y no contiene mensaje ni clase de la excepcion.

## H-AUTH-05 - Secreto fijo y CORS global

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-05. El secreto esta en codigo y CORS usa `/.*/` (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8`; `auth/src/main/resources/application.properties:4-7`).
- **Problema:** el secreto no puede rotarse externamente y la expresion CORS permite origenes no restringidos.
- **Cambio propuesto:** cargar la clave de firma desde configuracion externa de Quarkus, fallar de forma segura si falta en el perfil de ejecucion que firma tokens, y no almacenar secretos reales en el repositorio. Sustituir el origen global por origenes permitidos configurables y acotados; definir valores locales de prueba y evitar un default permisivo. Mantener los metodos y headers requeridos por el cliente observado.
- **Archivos a tocar:** `auth/src/main/resources/application.properties`, `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o emisor nuevo, y pruebas bajo `auth/src/test/java/com/bcp/workshop/auth/`. Cualquier secreto real se proveera fuera del repositorio; no se incluye en este plan.
- **Caracterizacion antes del cambio:** probar y registrar que el origen local usado por el frontend recibe los headers CORS actuales. Registrar tambien, como comportamiento a corregir, que un origen no permitido recibe actualmente el header permisivo; despues exigir que el origen configurado pase y uno ajeno sea rechazado. No ejecutar pruebas ni introducir secretos durante Discovery/planificacion.

## H-AUTH-06 - Responsabilidades mezcladas en AuthResource

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-06. `login` valida, consulta persistencia, crea token y construye la respuesta en el mismo metodo (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:24-50`).
- **Problema:** las reglas, el acceso a datos y el formato HTTP quedan acoplados, dificultando pruebas focalizadas y cambios seguros.
- **Cambio propuesto:** separar Resource (HTTP/validacion de request), servicio (autenticacion y flujo de negocio) y repositorio (SQLite), siguiendo `docs/GOOD_PRACTICES.md`. Mantener la firma HTTP, codigos de estado y JSON observado. Evitar duplicacion, anidamiento profundo y constantes magicas; no devolver `UserRecord` directamente.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`, clases nuevas de servicio/repositorio bajo `auth/src/main/java/com/bcp/workshop/auth/`, y pruebas bajo `auth/src/test/java/com/bcp/workshop/auth/`.
- **Caracterizacion antes del cambio:** completar pruebas HTTP para request nulo/campos requeridos (400), credenciales invalidas (401) y login valido (200 con los campos actuales). Agregar caso 500 controlado con la forma de error observada, evitando congelar detalles internos. Ejecutar y guardar el resultado antes de refactorizar.

## H-AUTH-07 - Versiones por revisar mediante SCA

- **Hallazgo:** `HALLAZGOS.md`, H-AUTH-07. `auth/pom.xml` declara Quarkus 3.27.4 y Commons Text 1.9 (`auth/pom.xml:13,49-50`); no hay evidencia aqui de un advisory confirmado.
- **Problema:** no se puede estimar el riesgo ni decidir una actualizacion basandose solo en las versiones declaradas; cambiar versiones sin compatibilidad comprobada puede romper el servicio.
- **Cambio propuesto:** primero resolver el arbol de dependencias y consultar los controles SCA existentes (CodeQL/Dependency Review y advisories pertinentes). Documentar versiones efectivas, advisories y versiones corregidas compatibles. Modificar `auth/pom.xml` unicamente si se confirma riesgo y se valida compatibilidad; justificar cualquier dependencia nueva.
- **Archivos a tocar:** inicialmente ninguno. Si el analisis confirma un cambio necesario, `auth/pom.xml` y las pruebas existentes/nuevas de `auth/` afectadas por la actualizacion.
- **Caracterizacion antes del cambio:** no aplica una prueba de comportamiento HTTP para una version; antes de editar el manifiesto, guardar `mvn dependency:tree` y el resultado del escaneo SCA como linea base. No se han ejecutado estos comandos ni se ha confirmado un CVE.

## Orden y condiciones de implementacion

1. Escribir y ejecutar las pruebas de caracterizacion indicadas antes de tocar cada comportamiento, empezando por SQL y persistencia.
2. Resolver H-AUTH-01 y H-AUTH-02 con pruebas aisladas y migracion local controlada; no mezclar el refactor de capas hasta estabilizar ese comportamiento.
3. Acordar el formato de token con sus consumidores antes de H-AUTH-03; no se inspeccionaron otros componentes ni se presume compatibilidad.
4. Aplicar H-AUTH-04 y H-AUTH-05 conservando status y formato observado en lo posible, con mensajes no sensibles y CORS restrictivo.
5. Separar capas en H-AUTH-06 tras caracterizar el contrato HTTP.
6. Resolver H-AUTH-07 solo con evidencia SCA. En cada etapa actualizar `HALLAZGOS.md` con resultados reales; no registrar aprobaciones ni pruebas no ejecutadas.

## Controles no ejecutados

- CodeQL remoto: no ejecutado en este recorrido local.
- Dependency Review remoto: no ejecutado en este recorrido local.

## Aprobación humana
- Revisor/a: Luis Salvador
- Fecha: 2026-10-26
- Decisión: Aprobado para implementar
- IDs aprobados: H-AUTH-01, H-AUTH-02
- Condiciones o comentarios: conforme

## Ronda de planificacion: tres pendientes de mayor prioridad

Seleccionados por severidad y, en empate, por el orden de HALLAZGOS.md: H-AUTH-02 y H-AUTH-03 (alta), seguidos por H-AUTH-04 (media). Esta selección documenta propuestas; no amplía la aprobación humana registrada arriba para H-AUTH-01 y H-AUTH-02 ni autoriza cambios de código en este paso.

## Item: H-AUTH-02 - Contraseñas legadas si falla la migración

- **Hallazgo de HALLAZGOS.md:** H-AUTH-02, Vulnerabilidad, estado `Pendiente`. PBKDF2 y migración transaccional están implementados, pero `initialize()` revierte la transacción, registra la excepción y continúa si la migración falla (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:35-45,71-88`).
- **Problema:** el servicio puede iniciar con credenciales legadas aún en texto plano; el fallo de migración queda oculto para el proceso de arranque.
- **Cambio propuesto:** fallar el inicio de forma cerrada si el esquema, el sembrado o la migración no terminan y confirman la transacción. Mantener el rollback y propagar una excepción de inicialización no sensible en lugar de imprimirla y continuar. No permitir que el login trate una contraseña legada sin migrar como válida. No agregar dependencias.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`; pruebas en `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` o una prueba nueva `LegacyDatabaseTest.java` bajo el mismo paquete.
- **Prueba antes de tocar producción:** con una SQLite temporal, insertar una fila legada y crear un trigger local que fuerce el fallo del `UPDATE` de migración. Primero escribir una prueba que espere que `initialize()` propague un fallo de inicialización y que la transacción no deje cambios parciales; registrar que la versión actual no satisface esa expectativa porque absorbe la excepción. Añadir también un caso exitoso que verifique login con la contraseña legada después de migrar.
- **Contrato:** no cambia la ruta ni el JSON de `POST /auth/login`; si la inicialización falla, el servicio no debe presentarse como iniciado.

## Item: H-AUTH-03 - Token firmado con expiración verificable

- **Hallazgo de HALLAZGOS.md:** H-AUTH-03, Vulnerabilidad, estado `Pendiente`. El token actual serializa username, rol, timestamp y secreto fijo, y lo codifica con Base64 sin firma (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,12-15`).
- **Problema:** Base64 no protege la integridad ni demuestra autenticidad; el consumidor no puede confiar en los datos del token ni validar criptográficamente su expiración.
- **Cambio propuesto:** reemplazar la codificación casera por una implementación JWT compatible con Quarkus, mantenida y con firma, expiración y claims de identidad/rol explícitos. Mantener el endpoint, el status de éxito y el sobre JSON observado (`token`, `expiresIn`, `user`, `debug`); el valor de `token` cambiará a un JWT verificable, como pide este hallazgo. Justificar cualquier dependencia antes de añadirla.
- **Dependencia de alcance:** la clave no puede quedar hardcodeada. Su origen externo corresponde al hallazgo independiente H-AUTH-05, que no está en esta selección. Antes de implementar H-AUTH-03, acordar/configurar esa dependencia bajo su propio alcance; no resolver CORS ni marcar H-AUTH-05 como incluido en este item.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java`, `auth/src/test/java/com/bcp/workshop/auth/` (prueba de token y/o `AuthResourceTest.java`) y `auth/pom.xml` solo si la biblioteca elegida lo justifica. La configuración de clave queda condicionada al plan separado de H-AUTH-05.
- **Prueba antes de tocar producción:** caracterizar una respuesta de login válida en el contrato de transporte: status 200, nombres/tipos de campos, `expiresIn` y datos del usuario; capturar también cómo se compone hoy el token sin convertir el secreto fijo en una aserción contractual. Después probar firma verificable, claims username/rol, expiración y rechazo de token alterado o vencido con la biblioteca seleccionada.
- **Contrato:** el formato del campo `token` cambiará expresamente por H-AUTH-03. Actualizar la descripción observada de `docs/ENDPOINTS.md` solo en la implementación/documentación posterior y registrar compatibilidad externa como riesgo mientras no exista confirmación de consumidores.

## Item: H-AUTH-04 - Errores HTTP 500 sin detalles internos

- **Hallazgo de HALLAZGOS.md:** H-AUTH-04, Vulnerabilidad, estado `Pendiente`. El recurso devuelve `error.getMessage()` y `error.getClass().getName()` (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:54-58`).
- **Problema:** el body puede revelar mensajes, clases y datos internos del servidor.
- **Cambio propuesto:** responder con status 500 y mensaje genérico constante, por ejemplo `{"message":"Internal server error"}`, sin devolver nombre de clase ni texto de excepción. Registrar el detalle solo en el servidor, sin credenciales. Conservar la ruta y los status 400/401/200.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java` y `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Prueba antes de tocar producción:** usar el doble de `LegacyDatabase` en una prueba para provocar una excepción con mensaje conocido y otra sin mensaje. Registrar en la caracterización actual el status 500, las claves y los valores que hoy se exponen; no congelar esos detalles como resultado deseado. Tras el cambio, comprobar que ambas respuestas mantienen status 500 y solo revelan el mensaje genérico.
- **Contrato:** el formato de error 500 cambia explícitamente por H-AUTH-04. No cambiar las demás respuestas documentadas; actualizar posteriormente `docs/ENDPOINTS.md` con la forma nueva cuando se implemente y valide el item.
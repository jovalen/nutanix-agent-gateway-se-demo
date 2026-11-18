# Quién decide durante una incidencia de checkout

## La conversación con el cliente

Abre con «Son las 10:04. Algunos clientes ya no pueden pagar. ¿Qué necesita saber la persona de guardia antes de intervenir?». Pulsa **Investigate incident** y despliega **Evidence behind this finding**. Los fallos pasan del 0,2 % al 7,1 % dos minutos después de un cambio en el pool de conexiones. El runbook marca un umbral del 5 % para solicitar una revisión. La coincidencia temporal justifica investigar el cambio. Para confirmar causalidad pediríamos errores por versión o compararíamos las instancias del despliegue anterior.

La pregunta para negocio es «¿qué podemos comunicar ahora?». Pulsa **Draft customer update** y muestra el contenido exacto remitido al modelo. El boletín es fijo, autorizado de antemano y específico de este escenario. Para producción habría que generar una proyección de campos aprobados desde el estado vigente, validar su frescura y registrar quién autorizó publicar. **Open rollback review** solo registra la decisión en la sesión del presentador.

## Tres decisiones distintas

| Decisión | Propietario | Observación que la acredita |
|---|---|---|
| Qué evidencia falta | Planificador privado dentro de un bucle acotado | En live escoge el orden de tres lecturas obligatorias y genera la hipótesis. El orquestador valida cada nombre, impide repeticiones y exige las tres evidencias antes del resumen. En ensayo el orden es determinista. |
| Dónde enviar el contexto | Router de la app, según la tarea | La investigación solo tiene rutas privadas. El redactor recibe el boletín; su primera ruta es hosted. La garantía depende también de la composición real de cada endpoint en NAI. |
| Qué backend sirve y qué herramientas expone una identidad | Operador de NAI | Configuración Load Balance o Fallback Order en el Unified Endpoint; asociación de clave y herramientas en el conector. Comprobar el proveedor real en plataforma, porque un alias en la respuesta puede ocultar el backend. |

El contexto de investigación persiste en el orquestador durante la ejecución. Cada llamada devuelve una decisión JSON. La app actúa como cliente MCP y entrega la evidencia al modelo en la siguiente iteración. El modelo no necesita conocer la clave MCP. Los registros son sintéticos incluso en live. La identidad de comunicaciones del experimento permite comparar el perímetro que tendría otra aplicación; el modelo redactor de este ejemplo nunca recibe esa credencial.

## El momento para un arquitecto

En el tenant de laboratorio, registra el servidor MCP sintético y configura dos claves para el mismo conector. Operaciones descubre las tres herramientas. Comunicaciones descubre solo read_runbook. Activa la prueba explícita según el README. Antes de pulsar **Test restricted read**, pregunta «¿Ocultar una herramienta del catálogo basta para impedir su ejecución si ya conozco su nombre?».

1. **Compare MCP identities** consulta tools/list con ambas claves. Enseña los catálogos devueltos.
2. **Test restricted read** ejecuta la misma lectura sintética con ambas identidades. La primera acredita que el servidor y la herramienta funcionan; la segunda comprueba el resultado para la identidad restringida. Si obtiene datos la pantalla señala acceso inesperado.
3. Contrasta el fallo con el registro del conector y con la asociación de la clave. Una excepción genérica, un problema TLS o una credencial caducada dejan el diagnóstico abierto. No se muestran datos privados de la lectura en el navegador.
4. Para una PoC, acuerda con seguridad el criterio de aceptación: catálogo correcto, control positivo, lectura restringida fallida por la política esperada y evidencias del mismo intervalo. La visibilidad del catálogo por sí sola solo prueba descubrimiento.

## Qué cambia al comparar plataformas

| Alternativa | Qué reconoce el SE | Qué debe evaluar el cliente |
|---|---|---|
| LiteLLM | Implementa grupos de modelos, reintentos, cooldowns y fallback. Su propio playground ya permite provocar una caída. | Si ya opera bien el serving y solo busca políticas de proxy, ese requisito por sí solo aporta poca diferenciación. |
| Kong AI Gateway | Ofrece proxy multi-proveedor, capacidades de routing semántico y MCP, incluida la exposición de APIs existentes como herramientas. | Evaluar la inversión previa en gestión de APIs y quién operará los endpoints de inferencia privados. |
| NAI con Agent Gateway | NAI opera endpoints de inferencia privada y permite incluir proveedores externos o Remote NAI en Unified Endpoints. El conector vincula claves a herramientas expuestas. | Pedir que el operador enseñe el despliegue privado, composición del endpoint, claves, permisos y evidencia de una ejecución. El valor diferencial propuesto es el alcance operativo integrado. |

Fuentes de producto consultadas el 18 de noviembre de 2026: [Nutanix sobre estrategias de routing y Remote NAI](https://www.nutanix.com/tech-center/blog/run-your-ai-in-the-cloud-or-dont-thats-the-point), [Nutanix sobre permisos MCP](https://www.nutanix.com/tech-center/blog/governing-ai-agents-with-mcp-connectors-in-nai), [NAI 2.8](https://next.nutanix.com/product-updates/nutanix-enterprise-ai-2-8-45849), [LiteLLM Router](https://docs.litellm.ai/docs/router/learn/reliability), [LiteLLM Playground](https://docs.litellm.ai/router-playground), [Kong AI Gateway](https://developer.konghq.com/ai-gateway/architecture/), [Kong changelog](https://developer.konghq.com/gateway/changelog/).

## SRE e inferencia privada

El botón de fallback inyecta un timeout antes del primer envío y la app reintenta en el backup privado. Para medir failover nativo, configura un Unified Endpoint de laboratorio con Fallback Order y dos backends permitidos, aplica el fallo en el upstream aislado de la v1 y usa una sola petición de cliente al mismo endpoint. Correlaciona el éxito con los intentos upstream y la identidad del backend. Si la evidencia del tenant solo muestra el alias, deja la identidad del backend sin confirmar.

Para KV cache, distingue el modelo lógico de sus réplicas. Dos peticiones al mismo modelo pueden llegar a réplicas con estados de caché distintos. Primero fija modelo y réplica, usa un prefijo suficientemente largo y único para ese ensayo y cambia solo el sufijo. Compara tokens de prefijo reutilizados o deltas de los contadores del motor en un intervalo aislado. Registra TTFT con streaming bajo la misma carga y longitud. La latencia total que mide esta app incluye generación; no equivale a TTFT. Repite con una réplica fría para aislar el efecto de la localidad. La reutilización ahorra trabajo de prefill; los tokens nuevos siguen requiriendo decoding. El ejemplo local de atención es pedagógico. Verifica versión y soporte antes de presentar cache-aware routing u offload GPU→CPU, funciones distintas.

Referencia: [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/).

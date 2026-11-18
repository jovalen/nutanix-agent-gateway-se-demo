# Nutanix Gear · Elección del orquestador de agentes

**Decisión de diseño · 18 de noviembre de 2026.** Usar LangGraph en Python para coordinar la ejecución. La integración con los modelos y la observabilidad del tenant NAI se validarán durante el despliegue.

## La prueba que determina la elección

Una clienta abre el pedido de una taza, adjunta una fotografía y explica por voz que le ha llegado rota y que necesita otra antes del viernes. Para resolverlo, el supervisor puede encargar en paralelo a Privacidad que inspeccione la imagen y a Pedidos que compruebe el artículo y la fecha de entrega. Con ambos resultados puede pedir una foto más clara o continuar con Visión, Posventa y Disponibilidad.

La ejecución debe poder esperar mientras la clienta decide si acepta la sustitución. Tras la confirmación, la tienda debe crear un solo reemplazo incluso si se repite el clic o se reintenta la operación. En una segunda pestaña, el SE debe poder recorrer los eventos de esa misma ejecución y explicar por qué cambió el plan.

## Alternativas consideradas

| Opción | Ventaja para la tienda | Coste o condición para elegirla |
|---|---|---|
| LangGraph | El estado del caso, la delegación dinámica, el trabajo paralelo y la pausa para confirmación se pueden representar explícitamente. Es una buena base para explicar cada transición en el visor. | Hay que diseñar el estado, combinar las respuestas paralelas y configurar la persistencia. Al reanudar un nodo interrumpido puede volver a ejecutarse código del nodo. El backend debe hacer idempotente la creación del reemplazo. |
| CrewAI | Su modelo de roles, tareas y manager facilita explicar la delegación entre especialistas. Los Flows permiten coordinar etapas y conservar estado. | En este caso habría que asignar con claridad qué decisiones corresponden al Flow y cuáles al manager de la Crew, y registrar esa distinción en el visor. Sería una buena elección para un taller centrado en repartir trabajo entre agentes. |
| Microsoft Agent Framework | Sus workflows, orquestaciones concurrentes e intervención humana cubren la bifurcación y la confirmación del caso. Microsoft lo presenta como sucesor directo de AutoGen y Semantic Kernel. | El equipo tendría que adoptar su modelo de ejecutores, eventos y reanudación. Es la alternativa más cercana para este diseño, especialmente si los partners ya trabajan con este ecosistema. |
| OpenAI Agents SDK | El supervisor puede invocar especialistas como herramientas. Ofrece estado reanudable, trazas y mecanismos para componer ejecuciones paralelas. | Habría que adaptar los eventos al lenguaje del visor, configurar el destino de las trazas y probar las capacidades de los modelos privados detrás del gateway, en particular las llamadas a herramientas y las salidas estructuradas. |

## Por qué elegimos LangGraph

El caso combina decisiones abiertas y condiciones que la tienda debe imponer. El supervisor puede variar el plan al recibir una foto borrosa o descubrir que el pedido ya se repuso. El código valida los pasos permitidos, espera la confirmación del cliente y conserva el vínculo entre la propuesta y el pedido. LangGraph encaja porque permite expresar ese reparto y guardar el punto en que se encuentra cada caso. La elección se basa en el diseño del taller; la comparación recoge capacidades documentadas y costes de integración previstos.

| Componente | Decisión de la que responde |
|---|---|
| Supervisor | Qué evidencia falta, qué especialista puede obtenerla y cuándo revisar el plan. |
| LangGraph | Qué tareas del plan pueden ejecutarse, cómo incorporar sus resultados al estado y desde qué punto reanudar. |
| Model router de la aplicación | Qué endpoint admite la tarea según la modalidad y la clasificación de los datos. Una imagen con PII o clasificación incierta requiere una ruta privada. |
| Nutanix Agent Gateway | Qué backend intenta dentro del Unified Endpoint, según su configuración. El ensayo de fallo del redactor requiere comprobar el segundo intento en el tenant. |
| Conector MCP y backend de la tienda | Qué herramientas puede invocar cada identidad y si procede crear el reemplazo asociado a la confirmación del cliente. |

## Qué enseña el SE

En la caja de Visión, el SE puede comparar dos ejecuciones y explicar por qué el mismo especialista utilizó dos rutas diferentes. En la caja de Posventa puede señalar qué política justificó la propuesta. En el evento de confirmación puede distinguir la recomendación del agente de la escritura autorizada por la clienta. La repetición del visor lee los eventos registrados. Reanudar una ejecución pausada, en cambio, continúa el trabajo del pedido.

## Referencias primarias

- LangGraph: [patrones de orquestación](https://docs.langchain.com/oss/python/langgraph/workflows-agents) e [interrupciones y reanudación](https://docs.langchain.com/oss/python/langgraph/interrupts).
- CrewAI: [proceso jerárquico](https://docs.crewai.com/en/learn/hierarchical-process) y [Flows](https://docs.crewai.com/en/concepts/flows).
- Microsoft Agent Framework: [visión general](https://learn.microsoft.com/agent-framework/overview) y [confirmaciones humanas](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop).
- OpenAI Agents SDK: [orquestación](https://openai.github.io/openai-agents-python/multi_agent/), [modelos](https://openai.github.io/openai-agents-python/models/) y [trazas](https://openai.github.io/openai-agents-python/tracing/).
- Nutanix: [Unified Endpoints y estrategias de selección de backend](https://www.nutanix.com/tech-center/blog/run-your-ai-in-the-cloud-or-dont-thats-the-point).

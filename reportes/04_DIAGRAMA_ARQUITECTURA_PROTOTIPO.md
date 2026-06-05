# Diagrama de arquitectura del prototipo

Fecha: 2026-06-01

Arquitectura lógica en 3 capas para el prototipo TT Ratones 2026. El diagrama está simplificado para presentación: muestra una entrada de video, el flujo de trabajo principal de procesamiento, la capa de presentación y la capa de datos/persistencia. Las flechas son direccionales y solo representan transferencia real de datos, comandos o resultados.

## Version recomendada para presentacion

La version mas limpia y controlada esta en:

`reportes/figuras/arquitectura_prototipo.html`

Se abre directamente en el navegador. Esta version evita paréntesis en el texto visible y organiza la arquitectura como una lamina horizontal con tres capas.

```mermaid
%% Arquitectura simplificada del prototipo TT Ratones 2026.
%% Estilo: tres capas y flujo principal de izquierda a derecha.
%% Regla de flechas: solo se usan conexiones direccionales cuando hay
%% transferencia real de datos, comandos o resultados.

flowchart LR
    video_in["Entrada de datos<br/><b>Video MP4</b><br/>videos_data/STEM.mp4"]

    subgraph ui_layer["PRESENTACION - Interfaz de usuario multipagina Streamlit"]
        direction LR
        ui_dashboard["Dashboard<br/>interactivo"]
        ui_tracks["Trayectorias<br/>y heatmaps"]
        ui_experiments["Gestion de<br/>experimentos"]
        ui_events["Edicion manual<br/>de eventos"]
        ui_reports["Reportes y<br/>exportaciones"]
    end

    subgraph workflow_layer["LOGICA DE NEGOCIO - Flujo de trabajo de procesamiento conductual"]
        direction LR
        m1["1<br/><b>Ingesta y<br/>preprocesamiento</b><br/>Python, OpenCV,<br/>FFmpeg"]
        m2["2<br/><b>Pose estimation</b><br/>YOLO Pose v4<br/>8 keypoints anatomicos"]
        m3["3<br/><b>Puente YOLO a SimBA</b><br/>Bridge CSV<br/>alineacion de formato"]
        m4["4<br/><b>Extraccion de<br/>caracteristicas</b><br/>242 features espaciales<br/>y de zona en SimBA"]
        m5["5<br/><b>Clasificacion de<br/>conducta</b><br/>RF SimBA Grooming<br/>RF SimBA Thigmotaxis<br/>LSTM Rescue"]
        m6["6<br/><b>Renderizado<br/>multimodal</b><br/>Video anotado<br/>CSV trayectoria<br/>Timelogs de eventos"]
    end

    subgraph data_layer["DATOS Y PERSISTENCIA - PostgreSQL + artefactos del proyecto"]
        direction LR
        db_meta["Metadatos<br/>experimentos, usuarios,<br/>tratamientos"]
        db_roi["Configuracion<br/>ROIs en JSONB<br/>zonas de interes"]
        db_metrics["Metricas<br/>agregadas y resultados<br/>de analisis"]
        db_audit["Historial auditado<br/>ediciones manuales<br/>behavior_edits"]
        files["Artefactos locales<br/>keypoints_yolo, SimBA,<br/>modelos, resultados_yolo"]
    end

    %% Flujo principal de datos/procesamiento.
    video_in --> m1
    m1 --> m2
    m2 --> m3
    m3 --> m4
    m4 --> m5
    m5 --> m6

    %% La UI dispara acciones especificas; no es una conexion generica.
    ui_experiments -->|registra experimento| m1
    ui_events -->|corrige eventos| db_audit
    ui_reports -->|solicita exportacion| m6

    %% Resultados consultados por la UI.
    m6 -->|publica resultados| ui_dashboard
    m6 -->|genera visualizaciones| ui_tracks
    db_metrics -->|alimenta reportes| ui_reports

    %% Persistencia usada por el flujo de trabajo.
    m1 -->|guarda metadatos| db_meta
    db_roi -->|provee zonas| m4
    m2 -->|guarda keypoints| files
    m3 -->|guarda bridge CSV| files
    m4 -->|guarda features| files
    files -->|features y modelos| m5
    m6 -->|guarda metricas| db_metrics
    m6 -->|guarda videos y CSV| files

    %% Estilos institucionales.
    classDef input fill:#ffffff,stroke:#c49a3a,color:#4a2c00,stroke-width:2px;
    classDef ui fill:#fff8ef,stroke:#8a1538,color:#4b001d,stroke-width:1.5px;
    classDef workflow fill:#fffdf8,stroke:#c49a3a,color:#4a2c00,stroke-width:1.5px;
    classDef data fill:#f8fff8,stroke:#2f7d32,color:#143b16,stroke-width:1.5px;
    classDef important fill:#8a1538,stroke:#8a1538,color:#ffffff,stroke-width:2px;

    class video_in input;
    class ui_dashboard,ui_tracks,ui_experiments,ui_events,ui_reports ui;
    class m1,m2,m3,m4,m5,m6 workflow;
    class db_meta,db_roi,db_metrics,db_audit,files data;
```

## Como renderizarlo

```bash
npx @mermaid-js/mermaid-cli -i reportes/figuras/arquitectura_prototipo.mmd -o reportes/figuras/arquitectura_prototipo.svg
npx @mermaid-js/mermaid-cli -i reportes/figuras/arquitectura_prototipo.mmd -o reportes/figuras/arquitectura_prototipo.png -b white
```

Archivos generados:

- `reportes/figuras/arquitectura_prototipo.mmd`
- `reportes/figuras/arquitectura_prototipo.svg`
- `reportes/figuras/arquitectura_prototipo.png`

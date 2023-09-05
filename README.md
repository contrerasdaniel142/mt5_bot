                                                    mt5_bot
Bot de MT5 para Operaciones Bursátiles

            Descripción
El proyecto es un bot de trading desarrollado en la plataforma MetaTrader 5 (MT5) diseñado para operar en los mercados financieros de manera automatizada y eficiente. Este bot se diferencia por su capacidad para conectarse a la API de Alpaca y utilizarla como fuente de datos y ejecución de operaciones.

            Características Clave
1) Días de Mercado: El bot puede identificar y operar únicamente en los días de mercado, utilizando la información proporcionada por la API de Alpaca para determinar cuándo están abiertos los mercados y cuándo deben realizarse las operaciones.

2) Estrategias de Trading: El bot implementa estrategias de trading definidas previamente. Puede realizar operaciones de compra y venta basadas en indicadores técnicos, análisis fundamental o cualquier otra estrategia personalizada diseñada por el usuario.

3) Multiproceso: Utiliza multiproceso para ejecutar tareas de forma paralela y aumentar la velocidad de procesamiento. Esto permite realizar múltiples operaciones simultáneas y aprovechar las oportunidades de mercado de manera más eficiente.

4) Gestión de Riesgos (En progreso): Incorpora sistemas de gestión de riesgos para proteger la inversión. Esto incluye límites de pérdida predefinidos y la capacidad de detener automáticamente las operaciones en caso de condiciones de mercado adversas.

5) Registro de Actividades (En progreso): El bot mantiene un registro detallado de todas las actividades de trading, facilitando la revisión y el análisis posterior de las operaciones realizadas.

            Beneficios
- Automatización: Elimina la necesidad de realizar operaciones manuales, ahorrando tiempo y reduciendo errores.
- Mayor Eficiencia: El uso de multiproceso permite aprovechar las oportunidades de mercado de manera más rápida y efectiva.
- Datos Precisos: La conexión a la API de Alpaca garantiza el acceso en horarios con movimiento financiero.
- Gestión de Riesgos (En progreso): Ayuda a proteger la inversión a través de estrategias de gestión de riesgos.
- Objetivos del Proyecto
- El objetivo principal del proyecto es crear un bot de trading confiable y eficiente que permita a los usuarios automatizar sus estrategias de inversión en los mercados financieros utilizando la plataforma MT5 y la API de Alpaca.


                                            Instrucciones de Instalación

Siga estos pasos para configurar el entorno de desarrollo:

            Instalar Python 3:
Asegúrese de tener Python 3 instalado en su sistema.

            Windos:
- Crear un Entorno Virtual
    $ python -m venv venv

- Activar el Entorno Virtual
    $ .\venv\Scripts\activate

- Instalar Dependencias
    $ pip install -r requirements.txt


## Configuración del Archivo .env

Para utilizar este bot de trading, es necesario configurar un archivo `.env` que contenga las siguientes variables de entorno:

### MT5 KEYS
- `MT5_LOGIN`: Tu número de inicio de sesión de MetaTrader 5.
- `MT5_PASSWORD`: Tu contraseña de MetaTrader 5.
- `MT5_SERVER`: El servidor de MetaTrader 5 al que deseas conectarte.
- `MT5_PATH`: La ruta al archivo ejecutable de MetaTrader 5 en tu sistema (por ejemplo, `'C:\Program Files\FTMO MetaTrader 5\terminal64.exe'`).

### ALPACA KEYS
- `ALPACA_API_KEY_ID`: Tu ID de clave API de Alpaca.
- `ALPACA_API_SECRET_KEY`: Tu clave secreta de API de Alpaca.

Asegúrate de crear un archivo `.env` en la raíz de tu proyecto y definir estas variables con los valores correspondientes antes de ejecutar el bot. Mantén este archivo confidencial y no lo incluyas en el control de versiones para proteger tus claves de acceso.

#region Descripción:
# Inicia el mt5_bot  
#endregion
#region importaciones
from controller.bot_controller import BotController
#endregion
if __name__ == '__main__':
    # Crea una instancia de BotController y llama a su método start
    bot = BotController()
    bot.start()
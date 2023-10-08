def _convert_time_to_mt5(self, date: datetime) -> datetime:
        """
        Suma 5 horas a la fecha y hora proporcionada.

        Args:
            date (datetime): Fecha y hora en formato UTC.

        Returns:
            datetime: La fecha y hora resultante después de sumar 5 horas.
        """
        # Suma 5 horas a la fecha y hora original
        dt_mt5 = date + timedelta(hours=5)
        
        return dt_mt5
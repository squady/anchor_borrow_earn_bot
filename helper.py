class Helper:
    @staticmethod
    def is_number(string: str):
        is_number = False
        try:
            float(string)
            is_number = True

        except ValueError:
            is_number = False
        
        return is_number

    @staticmethod
    def to_human_value(value: float):
        return round((value / 1_000_000),3)

    @staticmethod
    def to_terra_value(value: float):
        return round((value * 1_000_000),3)


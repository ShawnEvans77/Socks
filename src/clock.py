class Clock:
    def __init__(self, time_str: str):

        hour_int = int(time_str[:-2])
        
        match time_str[-2:]:
            case "PM":
                self.hour = hour_int if hour_int == 12 else hour_int + 12
            case "AM":
                self.hour = 0 if hour_int == 12 else hour_int

    def __sub__(self, other) -> int:
        return other.hour - self.hour
    
    def __str__(self) -> str:
        return str(self.hour)
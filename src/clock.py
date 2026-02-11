class Clock:
    """A simple class that recieves Strings in the form "12PM", "3AM", etc, then turns them into objects.
    We use this class for easily determining the amount of hours passed between two given times.
    
    Attributes
        hour - The hour this clock object represents, stored in 24 hour format.     
    """

    def __init__(self, time_str: str):
        hour_int = int(time_str[:-2])
        
        match time_str[-2:]:
            case "PM": self.hour = hour_int if hour_int == 12 else hour_int + 12
            case "AM": self.hour = 0 if hour_int == 12 else hour_int

    def __sub__(self, other) -> int:
        return other.hour - self.hour
    
    def __str__(self) -> str:
        return str(self.hour)
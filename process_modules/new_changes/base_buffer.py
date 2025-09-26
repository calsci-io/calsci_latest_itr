from abc import ABC, abstractmethod

class BaseBuffer(ABC):
    def __init__(self, rows=7, cols=21):
        self.rows = rows
        self.cols = cols
        self.total_buffer_size = self.rows * self.cols
        self.display_buffer = []
        self.refresh_area = ()

    @abstractmethod
    def update_buffer(self, input=""):
        raise NotImplementedError(f"Subclass must implement {self.update_buffer.__name__}")
    
    @abstractmethod
    def all_clear(self):
        raise NotImplementedError(f"Subclass must implement {self.all_clear.__name__}")

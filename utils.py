def undo_step(func):
    def wrapper(self, *args, **kwargs):
        self.song().begin_undo_step()
        try:
            result = func(self, *args, **kwargs)
        finally:
            self.song().end_undo_step()
        return result
    return wrapper

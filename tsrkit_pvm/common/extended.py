from typing import Any


class ExtendedList(list):
    """List which allows accessing elements out of bound, returns a default value if so"""

    def __init__(self, *args, default=None):
        super().__init__(*args)
        self.DEFAULT = default

    def __getitem__(self, index: int | slice):
        if isinstance(index, int):
            if index >= len(self) or index < -len(self):
                return self.DEFAULT
            return super().__getitem__(index)
        elif isinstance(index, slice):
            # Handle slice objects properly
            start, stop, step = index.indices(len(self))
            res = []
            for i in range(start, stop, step):
                res.append(self.__getitem__(i))
            return res

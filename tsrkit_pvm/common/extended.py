from typing import Any, Union, overload, SupportsIndex


class ExtendedList(list):
    """List which allows accessing elements out of bound, returns a default value if so"""

    def __init__(self, *args: Any, default: Any = None) -> None:
        super().__init__(*args)
        self.DEFAULT = default

    @overload
    def __getitem__(self, index: SupportsIndex) -> Any: ...
    
    @overload  
    def __getitem__(self, index: slice) -> list[Any]: ...

    def __getitem__(self, index: Union[SupportsIndex, slice]) -> Any:
        if isinstance(index, slice):
            # Handle slice objects properly
            start, stop, step = index.indices(len(self))
            res = []
            for i in range(start, stop, step):
                res.append(self.__getitem__(i))
            return res
        else:
            # Handle int index
            int_index = int(index)
            if int_index >= len(self) or int_index < -len(self):
                return self.DEFAULT
            return super().__getitem__(int_index)

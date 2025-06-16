class Tensor:
    pass

class no_grad:
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc, tb):
        pass

def from_numpy(arr):
    return Tensor()

def load(*_a, **_k):
    return {}


class nn:
    class Module:
        pass


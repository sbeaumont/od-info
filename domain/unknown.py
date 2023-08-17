class Unknown(object):
    def __add__(self, other):
        return self

    def __sub__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __truediv__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __rsub__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __rtruediv__(self, other):
        return self

    def __round__(self, n=None):
        return self

    def __trunc__(self):
        return self

    def __str__(self):
        return "Unknown"

    def __repr__(self):
        return "Unknown()"

    def __getitem__(self, item):
        return self

    def __getattr__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __float__(self):
        return 0.0

    def __int__(self):
        return 0

    def __lt__(self, other):
        return self

    def __gt__(self, other):
        return self



from collections import Counter


class AttrDict(dict):
    """Dictionary subclass whose entries can be accessed by attributes
    (as well as normally). Most of the code is from stackoverflow.
    """

    def __getattr__(self, name):
        if name in self:
            return self[name]

    def __setattr__(self, name, value):
        self[name] = self.from_nested_dict(value)

    def __delattr__(self, name):
        if name in self:
            del self[name]

    # to allow pickling
    def __getstate__(self):
        return self.__dict__

    # to allow pickling
    def __setstate__(self, d):
        self.__dict__.update(d)

    def to_dict(self):
        d = {}
        for name in self:
            if isinstance(self[name], self.__class__):
                d[name] = self[name].to_dict()

            else:
                d[name] = self[name]

        return d

    @classmethod
    def from_nested_dict(cls, data):
        """Construct nested AttrDicts from nested dictionaries. """
        if not isinstance(data, dict):
            return data
        elif isinstance(data, Counter):
            return data
        else:
            return cls({key: cls.from_nested_dict(data[key])
                        for key in data})

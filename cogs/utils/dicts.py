from collections import Counter


class AttrDict(dict):
    """Dictionary subclass whose entries can be accessed by attributes
    (as well as normally).
    https://stackoverflow.com/questions/38034377/object-like-attribute-access-for-nested-dictionary
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

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

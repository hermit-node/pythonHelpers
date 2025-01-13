from collections import OrderedDict

class SpecialD(dict):
    def __init__(self, *args, **kwargs):
        for each in args:
            if isinstance(each, dict):
                kwargs = {**each, **kwargs}  # Merge
        super().__init__(**kwargs)  # Initialize the dictionary

        for key, value in kwargs.items():
            if not key.startswith('__'):
                setattr(self, key, value)

    def copy_but(self, dict_obj=None, **kwargs):
        # Create a shallow copy of the current dictionary
        g = self.copy()

        # Update the copy with keys from dict_obj, if provided
        if isinstance(dict_obj, dict):
            g.update(dict_obj)

        # Update the copy with kwargs
        g.update(kwargs)

        # Return a new SpecialD instance
        return SpecialD(**g)

    def check_keys(self, keys):
        """
        Check if a list of keys exists in the dictionary.
        Raises a KeyError with the missing keys if any are not found.
        """
        if not isinstance(keys, list):
            keys = list(keys)
        missing_keys = [key for key in keys if key not in self]
        if missing_keys:
            raise KeyError(f"The following keys are missing: {missing_keys}")
        return True  # All keys are found

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        setattr(self, key, value)

    def __delitem__(self, key):
        super().__delitem__(key)
        if hasattr(self, key):
            delattr(self, key)

    def to_string(self, delimiter=", ", required_keys=[]):
        """
        Return a string of key=value pairs separated by the specified delimiter.
        """
        if required_keys:
            self.check_keys(required_keys)
            return delimiter.join(f"{key}={self[key]}" for key in required_keys)
        return delimiter.join(f"{key}={value}" for key, value in self.items())

    def ordered_one(self, reverse=False):
        g = OrderedDict(sorted(self.items(), reverse=reverse))
        g = SpecialD(g)
        return g
